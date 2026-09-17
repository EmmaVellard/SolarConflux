"""Trajectory retrieval from SPICE kernels, as an offline alternative to JPL Horizons.

Positions are read from SPICE in the ``J2000`` (ICRF-aligned) frame relative to the
Sun and then converted with SunPy's own Heliocentric Inertial transform, which is the
same transform the Horizons backend uses. Defining a custom HCI frame kernel relative
to SPICE's ``ECLIPJ2000`` instead disagrees with the Horizons path by a constant 0.28
arcsec in longitude, because SPICE uses the IAU 1976 obliquity while Astropy uses
IAU 2006.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .bodies import validate_body_names
from .validation import parse_datetime, step_to_seconds, validate_date_range

NAIF = "https://naif.jpl.nasa.gov/pub/naif/"

# Bodies whose ephemerides are simply not published as SPICE kernels.
UNSUPPORTED_BODIES: Dict[str, str] = {
    "ACE": (
        "ACE ephemeris is distributed as SSCWeb/CDAWeb orbit data, not as SPICE kernels; "
        "no public SPK exists."
    ),
    "SDO": (
        "SDO ephemeris is distributed as GSFC definitive orbit files / SSCWeb data, not as "
        "SPICE kernels; no public SPK exists."
    ),
}

ESA_SPICE = "https://spiftp.esac.esa.int/data/SPICE/"
APL_SPP = "https://sppgway.jhuapl.edu/MOC/ephemeris/"

# Archives NAIF does not mirror. These hosts are attempted, but were unreachable from the
# environment this was developed in, so neither path is verified. If a fetch fails the error
# points at manual placement instead: any .bsp dropped in the body's cache folder is used.
EXTERNAL_ARCHIVES: Dict[str, str] = {
    "Solar Orbiter": ESA_SPICE + "SOLAR-ORBITER/kernels/spk/",
    "PSP": APL_SPP + " (NAIF does not receive PSP operational kernels)",
}

# Kernel coverage that is narrower than the Horizons range advertised in bodies.py.
PARTIAL_COVERAGE: Dict[str, str] = {
    "Stereo-A": (
        "NAIF's STEREO-A_merged.bsp stops at 2018-12-31, is predicted rather than reconstructed "
        "after 2015-01-01, and differs from the ephemeris Horizons serves by a few thousand km "
        "(about 26 arcsec). Use source='horizons' where that matters."
    ),
    "SOHO": (
        "NAIF's SOHO kernels stop at 2014-12-01 and have a gap from 1998-08-19 to 1998-09-25 "
        "(the loss-of-attitude period)."
    ),
}

# de440s.bsp holds no Mars (499) or Jupiter (599) barycentre-relative segments, only the
# system barycentres. The offset is 0.2 m for Mars and ~230 km for Jupiter -- far below the
# resolution of the alignment screening this package performs.
_TARGETS: Dict[str, Tuple[str, int]] = {
    "BepiColombo": ("-121", -121),
    "Solar Orbiter": ("-144", -144),
    "Europa Clipper": ("-159", -159),
    "PSP": ("-96", -96),
    "Stereo-A": ("-234", -234),
    "Juice": ("-28", -28),
    "Maven": ("-202", -202),
    "Messenger": ("-236", -236),
    "Juno": ("-61", -61),
    "SOHO": ("-21", -21),
    "Venus": ("VENUS", 299),
    "Earth": ("EARTH", 399),
    "Mars": ("MARS BARYCENTER", 4),
    "Jupiter": ("JUPITER BARYCENTER", 5),
    "Sun": ("SUN", 10),
}

_GENERIC_KERNELS = (
    ("generic_kernels/lsk/", "naif0012.tls"),
    ("generic_kernels/spk/planets/", "de440s.bsp"),
)

# Bodies covered by the generic planetary ephemeris alone.
_DE440S_BODIES = frozenset({"Venus", "Earth", "Mars", "Jupiter", "Sun"})


class _Spec:
    """One kernel source: either an exact filename or a pattern resolved remotely."""

    def __init__(self, directory: str, filename: Optional[str] = None, pattern: Optional[str] = None,
                 latest: bool = False, window: Optional[Tuple[str, str]] = None,
                 window_from_name: Optional[str] = None, exclude: Optional[str] = None,
                 order_by: Optional[str] = None, base: str = NAIF):
        self.base = base
        self.directory = directory
        self.filename = filename
        self.pattern = re.compile(pattern) if pattern else None
        self.latest = latest
        self.window = window
        self.window_from_name = window_from_name
        self.exclude = re.compile(exclude) if exclude else None
        self.order_by = order_by


_MANIFEST: Dict[str, List[_Spec]] = {
    # ESA kernels mirrored by NAIF; the sequence number rolls, so resolve the newest.
    "BepiColombo": [_Spec("BEPICOLOMBO/kernels/spk/",
                          pattern=r"bc_mpo_fcp_\d+_\d+_\d+_v\d+\.bsp", latest=True)],
    "Juice": [_Spec("JUICE/kernels/spk/",
                    pattern=r"juice_orbc_\d+_\d+_\d+_v\d+\.bsp", latest=True)],
    # The long ref_trj is the *design* trajectory and disagrees with the flown one by
    # thousands of km, so it is furnished first only to fill gaps. Operational arcs then
    # override it, ordered by data cutoff (dco) so the newest solution wins -- SPICE gives
    # precedence to the last kernel furnished. Preliminary, no-burn and test arcs are
    # superseded by design and must not be loaded.
    "Europa Clipper": [
        _Spec("EUROPACLIPPER/kernels/spk/",
              "ref_trj_241014_340903_21F31_MEGA_L241014_A300411_LP05_V7_scpse.bsp"),
        _Spec("EUROPACLIPPER/kernels/spk/",
              pattern=r"trj_\d{6}-\d{6}-dco\d{10}-[\w\-]+-OD\d+-v\d+(?:-noburn)?\.bsp",
              exclude=r"(?i)(noburn|prelim|test|cancel)",
              window_from_name="trj", order_by="dco"),
    ],
    # Increasing precedence. The merge file is reconstructed only through 2013-05-14 and
    # predicted afterwards, so on its own it is ~3000 km off during cruise; the per-arc
    # spk_rec files carry the reconstructed trajectory and must override it. Some arcs
    # share a window and differ only by production date, so order by that.
    "Juno": [
        _Spec("JUNO/kernels/spk/", "spk_merge_110805_171017_130515.bsp", window=("2011-08-05", "2017-10-16")),
        _Spec("JUNO/kernels/spk/", "juno_rec_orbit.bsp", window=("2016-07-05", "2026-08-24")),
        _Spec("JUNO/kernels/spk/", pattern=r"spk_rec_\d{6}_\d{6}_\d{6}\.bsp",
              window_from_name="spk_rec", order_by="produced"),
    ],
    "Messenger": [_Spec(
        "pds/data/mess-e_v_h-spice-6-v1.0/messsp_1000/data/spk/",
        "msgr_040803_150430_150430_od431sc_2.bsp")],
    # No merged MAVEN SPK exists; pick only the per-interval files that overlap the request.
    "Maven": [
        _Spec("MAVEN/kernels/spk/", "trj_c_131118-140923_rec_v1.bsp", window=("2013-11-18", "2014-09-23")),
        _Spec("MAVEN/kernels/spk/", pattern=r"maven_orb_rec_\d{6}_\d{6}_v\d+\.bsp",
              window_from_name="maven"),
    ],
    # Not mirrored by NAIF, and neither host was reachable to verify. ESA's layout is stable
    # enough to attempt; the APL path for PSP is a best guess and may well 404. Both fall back
    # to hand-placed kernels, so a wrong URL degrades to the previous manual behaviour.
    "Solar Orbiter": [_Spec("SOLAR-ORBITER/kernels/spk/", base=ESA_SPICE,
                            pattern=r"solo_ANC_soc-orbit-stp_[\w\-]+\.bsp", latest=True)],
    "PSP": [_Spec("", base=APL_SPP, pattern=r"spp_(?:nom|ref|rec)_[\w\-]+\.bsp", latest=True)],
    "Stereo-A": [_Spec("STEREO/kernels/spk/", "STEREO-A_merged.bsp")],
    "SOHO": [_Spec("misc/MORE_PROJECTS/SOHO/kernels/spk/", pattern=r"soho_\d{4}[ab]?\.bsp",
                   window_from_name="soho")],
}

_furnished: set = set()


def kernel_dir() -> Path:
    """Return the local kernel cache directory."""
    configured = os.environ.get("SOLARCONFLUX_KERNEL_DIR")
    base = Path(configured).expanduser() if configured else Path.home() / ".solarconflux" / "kernels"
    return base


def spice_supported_bodies() -> List[str]:
    """Return bodies this backend can retrieve from NAIF without manual kernel placement."""
    return sorted(set(_MANIFEST) | _DE440S_BODIES)


def _reject_unsupported(bodies: Sequence[str]) -> None:
    for body in bodies:
        if body in UNSUPPORTED_BODIES:
            raise ValueError(
                f"{body} cannot be retrieved from SPICE kernels. {UNSUPPORTED_BODIES[body]} "
                f"Use source='horizons' for {body}."
            )


def _window_from_name(kind: str, name: str) -> Optional[Tuple[datetime, datetime]]:
    if kind == "maven":
        match = re.search(r"_(\d{6})_(\d{6})_", name)
        if not match:
            return None
        return (datetime.strptime(match.group(1), "%y%m%d"), datetime.strptime(match.group(2), "%y%m%d"))
    if kind == "spk_rec":
        match = re.search(r"spk_rec_(\d{6})_(\d{6})_\d{6}", name)
        if not match:
            return None
        return (datetime.strptime(match.group(1), "%y%m%d"), datetime.strptime(match.group(2), "%y%m%d"))
    if kind == "trj":
        match = re.search(r"trj_(\d{6})-(\d{6})-", name)
        if not match:
            return None
        return (datetime.strptime(match.group(1), "%y%m%d"), datetime.strptime(match.group(2), "%y%m%d"))
    if kind == "soho":
        match = re.search(r"soho_(\d{4})", name)
        if not match:
            return None
        year = int(match.group(1))
        return (datetime(year, 1, 1), datetime(year + 1, 1, 1))
    return None


def _overlaps(window: Optional[Tuple[datetime, datetime]], start: datetime, end: datetime) -> bool:
    if window is None:
        return True
    return window[0] <= end and window[1] >= start


def _list_remote(base: str, directory: str) -> str:
    url = base + directory
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            body = response.read().decode("utf-8", "replace")
    except Exception as exc:
        raise RuntimeError(f"Could not list the kernel directory {url}: {exc}") from exc
    return body


def _resolve(spec: _Spec, start: datetime, end: datetime) -> List[Tuple[str, str, str]]:
    """Return (base, directory, filename) triples for a spec, filtered to the requested window."""
    if spec.filename is not None:
        window = None
        if spec.window is not None:
            window = (parse_datetime(spec.window[0], "coverage start"),
                      parse_datetime(spec.window[1], "coverage end"))
        if not _overlaps(window, start, end):
            return []
        return [(spec.base, spec.directory, spec.filename)]

    listing = _list_remote(spec.base, spec.directory)
    names = sorted(set(spec.pattern.findall(listing)))
    if spec.exclude is not None:
        names = [n for n in names if not spec.exclude.search(n)]
    if not names:
        raise RuntimeError(
            f"No kernels matching {spec.pattern.pattern} were found in {spec.base}{spec.directory}."
        )
    if spec.latest:
        return [(spec.base, spec.directory, names[-1])]
    selected = [n for n in names if _overlaps(_window_from_name(spec.window_from_name, n), start, end)]
    if spec.order_by == "dco":
        selected.sort(key=lambda n: re.search(r"dco(\d{10})", n).group(1))
    elif spec.order_by == "produced":
        selected.sort(key=lambda n: re.search(r"_(\d{6})\.bsp$", n).group(1))
    return [(spec.base, spec.directory, name) for name in selected]


def _download(base: str, directory: str, filename: str, target: Path) -> None:
    url = base + directory + filename
    partial = target.with_suffix(target.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=300) as response:
            total = int(response.headers.get("Content-Length") or 0)
            # Announced unconditionally: some mission kernels are hundreds of megabytes and
            # a silent multi-minute stall looks like a hang.
            size = f"{total / 1e6:.0f} MB" if total else "unknown size"
            print(f"Downloading SPICE kernel {filename} ({size})...", file=sys.stderr, flush=True)
            with open(partial, "wb") as handle:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    handle.write(chunk)
    except Exception as exc:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download the SPICE kernel {url}: {exc}") from exc
    # Rename only once the body is complete, so an interrupted run cannot leave a
    # truncated kernel that SPICE would later load as valid.
    partial.replace(target)


def ensure_kernels(bodies: Sequence[str], start: datetime, end: datetime) -> Tuple[List[Path], List[Path]]:
    """Download any missing kernels and return them as (generic, mission) path lists."""
    cache = kernel_dir()
    generic_dir = cache / "generic"
    generic_dir.mkdir(parents=True, exist_ok=True)

    generic: List[Path] = []
    for directory, filename in _GENERIC_KERNELS:
        target = generic_dir / filename
        if not target.exists():
            _download(NAIF, directory, filename, target)
        generic.append(target)

    paths: List[Path] = []
    for body in bodies:
        if body in _DE440S_BODIES:
            continue
        body_dir = cache / body.replace(" ", "_")
        body_dir.mkdir(parents=True, exist_ok=True)
        found: List[Path] = []
        problem = None
        for spec in _MANIFEST.get(body, []):
            try:
                resolved = _resolve(spec, start, end)
            except RuntimeError as exc:
                # An unreachable or restructured archive should not lose kernels already on
                # disk, so remember the problem and fall back to whatever is cached.
                problem = exc
                continue
            for base, directory, filename in resolved:
                target = body_dir / filename
                if not target.exists():
                    try:
                        _download(base, directory, filename, target)
                    except RuntimeError as exc:
                        problem = exc
                        continue
                found.append(target)
        # Hand-placed kernels supplement the manifest, and are the only source for bodies
        # whose archive could not be reached.
        found.extend(p for p in sorted(body_dir.glob("*.bsp")) if p not in found)
        if not found:
            archive = EXTERNAL_ARCHIVES.get(body, "its mission archive")
            detail = f" The archive could not be used: {problem}" if problem else ""
            raise RuntimeError(
                f"No SPICE kernels are available for {body}. Download the mission SPK from "
                f"{archive} and place it in {body_dir}, or use source='horizons' for {body}."
                + detail
            )
        paths.extend(found)

    return generic, paths


def furnish(generic: Sequence[Path], mission: Sequence[Path]) -> None:
    """Load kernels so that the generic ephemeris takes precedence over mission SPKs.

    Mission SPKs routinely bundle planetary segments -- Juno's cruise merge contains the
    Sun, and Europa Clipper's reference trajectory contains most of the solar system. SPICE
    prefers the last kernel furnished, so loading those after de440s would silently replace
    planet and observer positions with whatever fidelity the mission file happened to carry,
    making every body's answer depend on which spacecraft was requested alongside it.
    Clearing the pool first also keeps repeated calls in one process deterministic.
    """
    import spiceypy

    spiceypy.kclear()
    _furnished.clear()
    for path in list(mission) + list(generic):
        resolved = str(Path(path).resolve())
        spiceypy.furnsh(resolved)
        _furnished.add(resolved)


def _time_grid(start: datetime, end: datetime, seconds: float) -> List[datetime]:
    times = []
    current = start
    delta = timedelta(seconds=seconds)
    while current <= end:
        times.append(current)
        current += delta
    return times


def _coverage_windows(naif_id: int) -> List[Tuple[float, float]]:
    """Return the ephemeris time intervals the loaded kernels cover for a body."""
    import spiceypy

    windows = spiceypy.stypes.SPICEDOUBLE_CELL(4000)
    for path in sorted(_furnished):
        if path.endswith(".bsp"):
            try:
                spiceypy.spkcov(path, naif_id, windows)
            except Exception:
                continue
    return [tuple(spiceypy.wnfetd(windows, i)) for i in range(spiceypy.wncard(windows))]


def _coverage_message(naif_id: int) -> str:
    import spiceypy

    try:
        spans = _coverage_windows(naif_id)
        if not spans:
            return "the loaded kernels contain no coverage for it"
        first = spiceypy.et2utc(spans[0][0], "ISOC", 0)
        last = spiceypy.et2utc(spans[-1][1], "ISOC", 0)
        return f"the loaded kernels cover {first} to {last}"
    except Exception:
        return "the loaded kernels do not cover the requested interval"


def get_spice_trajectories(
    body_list: Iterable[str],
    start_time: object,
    end_time: object,
    step: str = "60m",
    notes: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Fetch trajectories from SPICE kernels in the Heliocentric Inertial frame.

    When ``notes`` is given, a body whose kernels cover only part of the window is truncated
    and explained there rather than failing the request, and a body with no coverage at all
    is left out of the result instead of raising.
    """
    bodies = validate_body_names(body_list)
    validate_date_range(start_time, end_time)
    seconds = step_to_seconds(step)
    _reject_unsupported(bodies)

    try:
        import numpy as np
        import spiceypy
        from astropy.coordinates import CartesianRepresentation, HCRS, SkyCoord
        from astropy.time import Time
        import astropy.units as u
        from sunpy.coordinates import HeliocentricInertial
    except ImportError as exc:
        raise ImportError(
            "SPICE trajectory retrieval requires spiceypy, numpy, astropy and sunpy. "
            "Install SolarConflux with the 'spice' extra: pip install solarconflux[spice]."
        ) from exc

    start = parse_datetime(start_time, "start_time")
    end = parse_datetime(end_time, "end_time")
    times = _time_grid(start, end, seconds)

    furnish(*ensure_kernels(bodies, start, end))

    obstime = Time([t.isoformat() for t in times], scale="utc")
    ephemeris_times = [spiceypy.str2et(t.isoformat()) for t in times]

    trajectories: Dict[str, object] = {}
    for body in bodies:
        target, naif_id = _TARGETS[body]
        # Keep only the epochs the kernels actually cover. A mission whose ephemeris starts
        # or ends inside the requested window then contributes its covered portion instead of
        # failing the whole request, which is what spkezr would otherwise do at the first
        # uncovered epoch.
        spans = _coverage_windows(naif_id)
        if spans:
            usable = [
                index for index, et in enumerate(ephemeris_times)
                if any(lower <= et <= upper for lower, upper in spans)
            ]
        else:
            usable = list(range(len(ephemeris_times)))
        if not usable:
            message = f"SPICE lookup failed for {body!r} (NAIF {naif_id}): {_coverage_message(naif_id)}."
            if notes is None:
                raise RuntimeError(message)
            notes[body] = f"excluded: no SPICE coverage in this window, {_coverage_message(naif_id)}"
            continue
        if notes is not None and len(usable) < len(ephemeris_times):
            notes[body] = (
                f"truncated: kept {times[usable[0]]:%Y-%m-%d %H:%M} to {times[usable[-1]]:%Y-%m-%d %H:%M}, "
                f"the part within its SPICE coverage"
            )
        try:
            states = [spiceypy.spkezr(target, ephemeris_times[i], "J2000", "NONE", "SUN")[0][:3] for i in usable]
        except Exception as exc:
            raise RuntimeError(
                f"SPICE lookup failed for {body!r} (NAIF {naif_id}): {_coverage_message(naif_id)}."
            ) from exc
        xyz = np.asarray(states, dtype=float).T * u.km
        coord = SkyCoord(CartesianRepresentation(xyz), frame=HCRS(obstime=obstime[usable]))
        trajectories[body] = coord.transform_to(HeliocentricInertial())

    return trajectories
