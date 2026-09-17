"""Trajectory retrieval from JPL Horizons via SunPy, or from local SPICE kernels."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from .bodies import get_infos, validate_body_names
from .validation import parse_datetime, step_to_seconds, validate_date_range, validate_source, validate_step

# Horizons names the exact edge of a spacecraft's ephemeris when a request runs past it, for
# example: No ephemeris for target "MESSENGER (spacecraft)" after A.D. 2015-MAY-01 18:49:57 TDB
_COVERAGE_LIMIT = re.compile(
    r"No ephemeris for target .*? (prior to|after) A\.D\. "
    r"(\d{4})-([A-Z]{3})-(\d{2}) (\d{2}):(\d{2}):(\d{2})",
    re.IGNORECASE,
)
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
# The reported edge is TDB, which currently runs about 69 s ahead of UTC. Stepping this far
# inside the boundary keeps the clamped request safely within coverage.
_TDB_MARGIN = timedelta(seconds=70)


def get_info() -> None:
    """Print the list of supported bodies and their documented date ranges."""
    body_info = get_infos()
    print("Spacecraft and planets: (yyyy-mm-dd hh:mm)\n")
    for body, info in body_info.items():
        print(f"- {body}: {info['start']} to {info['end']}")
    print("\nFor more information, refer to the Horizons documentation.")


def get_trajectories(
    body_list: Iterable[str],
    start_time: object,
    end_time: object,
    step: str = "60m",
    source: str = "horizons",
) -> Dict[str, object]:
    """Fetch and convert trajectories to the Heliocentric Inertial frame.

    ``source`` selects the ephemeris backend: ``"horizons"`` queries JPL Horizons over
    the network, ``"spice"`` reads local SPICE kernels, and ``"prefer-spice"`` uses SPICE
    per body where it is available and Horizons for the rest. All return values in the
    same frame via the same SunPy transform. Unit tests can use
    :class:`solarconflux.geometries.TrajectoryPoint` instead of live queries.

    Use :func:`retrieve_trajectories` when the per-body backend actually used matters.
    """
    return retrieve_trajectories(body_list, start_time, end_time, step, source)[0]


def retrieve_trajectories(
    body_list: Iterable[str],
    start_time: object,
    end_time: object,
    step: str = "60m",
    source: str = "horizons",
) -> Tuple[Dict[str, object], Dict[str, str], Dict[str, str]]:
    """Fetch trajectories and report where each body came from and how it was adjusted.

    Returns ``(trajectories, provenance, notes)``. ``provenance`` maps each returned body to
    the backend that supplied it, which is what makes a mixed ``"prefer-spice"`` run
    interpretable. ``notes`` explains any body that was truncated to its ephemeris coverage
    or left out entirely; a body named there but absent from ``trajectories`` was excluded.

    A body whose ephemeris does not span the whole window no longer fails the request. It
    contributes the covered part, and takes no part in the geometry outside it.
    """
    normalized = validate_source(source)
    bodies = validate_body_names(body_list)
    notes: Dict[str, str] = {}

    if normalized == "prefer-spice":
        return _require_any_body(*_prefer_spice(bodies, start_time, end_time, step, notes))
    if normalized == "spice":
        from .spice import get_spice_trajectories

        trajectories = get_spice_trajectories(bodies, start_time, end_time, step, notes=notes)
        return _require_any_body(trajectories, {body: "spice" for body in trajectories}, notes)
    trajectories = _horizons_trajectories(bodies, start_time, end_time, step, notes=notes)
    return _require_any_body(trajectories, {body: "horizons" for body in trajectories}, notes)


def _require_any_body(
    trajectories: Dict[str, object], provenance: Dict[str, str], notes: Dict[str, str],
) -> Tuple[Dict[str, object], Dict[str, str], Dict[str, str]]:
    """Fail with the per-body reasons when the window covers none of the requested bodies.

    Dropping uncovered bodies leaves nothing to screen if every one of them was dropped. The
    reasons are already known at this point, so they are reported instead of letting the
    empty result surface later as a bare "At least one body must be selected".
    """
    if trajectories:
        return (trajectories, provenance, notes)
    reasons = "; ".join(f"{body}: {reason}" for body, reason in notes.items())
    raise ValueError(
        "None of the requested bodies have ephemeris coverage in this window. "
        + (reasons or "No coverage was reported for any requested body.")
    )


def _prefer_spice(
    bodies: Iterable[str], start_time: object, end_time: object, step: str,
    notes: Dict[str, str],
) -> Tuple[Dict[str, object], Dict[str, str], Dict[str, str]]:
    """Take each body from SPICE where possible, falling back to Horizons per body.

    Bodies are attempted one at a time so that a single body without kernels -- PSP and
    Solar Orbiter are not mirrored by NAIF, and ACE and SDO have no SPK at all -- does not
    force the whole request onto one backend.
    """
    from .spice import get_spice_trajectories

    trajectories: Dict[str, object] = {}
    provenance: Dict[str, str] = {}
    fallback: List[str] = []
    # A body whose kernels reach only part of the window has not really been served by SPICE:
    # SOHO's archived SPK stops in 2014 while Horizons still covers it to the present. Such a
    # body is retried against Horizons below and the longer series wins, so preferring SPICE
    # can never cost samples that the other backend would have supplied.
    partial: Dict[str, str] = {}
    for body in bodies:
        try:
            single: Dict[str, str] = {}
            got = get_spice_trajectories([body], start_time, end_time, step, notes=single)
            if body not in got:
                raise RuntimeError(single.get(body, "no SPICE coverage"))
            trajectories[body] = got[body]
            provenance[body] = "spice"
            if body in single:
                partial[body] = single[body]
            else:
                notes.update(single)
        except Exception as exc:
            logging.info("SPICE unavailable for %s, using Horizons instead: %s", body, exc)
            fallback.append(body)

    retried: Dict[str, str] = {}
    from_horizons: Dict[str, object] = {}
    if fallback or partial:
        try:
            from_horizons = _horizons_trajectories(
                fallback + list(partial), start_time, end_time, step, notes=retried
            )
        except Exception as exc:
            # Bodies already served by SPICE must survive a Horizons outage, so the retry is
            # allowed to fail: only the bodies SPICE could not supply at all are then lost.
            logging.info("Horizons unavailable while completing a prefer-spice run: %s", exc)
    for body in fallback:
        if body in from_horizons:
            trajectories[body] = from_horizons[body]
            provenance[body] = "horizons"
        if body in retried:
            notes[body] = retried[body]
    for body, spice_note in partial.items():
        if body in from_horizons and len(from_horizons[body]) > len(trajectories[body]):
            trajectories[body] = from_horizons[body]
            provenance[body] = "horizons"
            if body in retried:
                notes[body] = retried[body]
        else:
            notes[body] = spice_note
    # Restore the caller's ordering, which the two-pass fetch above does not preserve.
    ordered = {body: trajectories[body] for body in bodies if body in trajectories}
    return ordered, provenance, notes


def _parse_coverage_limit(message: str) -> Optional[Tuple[str, datetime]]:
    match = _COVERAGE_LIMIT.search(message)
    if not match:
        return None
    side, year, month, day, hour, minute, second = match.groups()
    key = month.upper()
    if key not in _MONTHS:
        return None
    edge = datetime(int(year), _MONTHS[key], int(day), int(hour), int(minute), int(second))
    return ("start" if side.lower() == "prior to" else "end", edge)


def _clamp_to_grid(
    start: datetime, end: datetime, seconds: float, side: str, edge: datetime
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Shrink a window to the samples inside a coverage edge, staying on the original grid.

    Samples must stay on the grid the other bodies use, otherwise the timestamps would not
    line up and the bodies could not be screened against each other.
    """
    span = timedelta(seconds=seconds)
    if side == "start":
        limit = edge + _TDB_MARGIN
        if limit > end:
            return (None, None)
        steps = max(0, -(-int((limit - start).total_seconds()) // int(seconds)))
        return (start + steps * span, end)
    limit = edge - _TDB_MARGIN
    if limit < start:
        return (None, None)
    steps = int((limit - start).total_seconds()) // int(seconds)
    return (start, start + steps * span)


def _horizons_trajectories(
    body_list: Iterable[str], start_time: object, end_time: object, step: str,
    notes: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    bodies = validate_body_names(body_list)
    validate_date_range(start_time, end_time)
    step = validate_step(step)

    try:
        from sunpy.coordinates import HeliocentricInertial, get_horizons_coord
    except ImportError as exc:
        raise ImportError(
            "Trajectory retrieval requires sunpy, astropy, and astroquery. "
            "Install SolarConflux with its runtime dependencies before querying Horizons."
        ) from exc

    body_info = get_infos()
    trajectories: Dict[str, object] = {}

    seconds = step_to_seconds(step)
    requested_start = parse_datetime(start_time, "start_time")
    requested_end = parse_datetime(end_time, "end_time")

    for body in bodies:
        body_id = body_info[body]["id"]
        try:
            coord = get_horizons_coord(
                body_id,
                {"start": start_time, "stop": end_time, "step": step},
            )
        except Exception as exc:
            # Horizons refuses the whole request rather than returning the covered part, but
            # it names the edge of coverage, so retry once against the samples inside it.
            limit = _parse_coverage_limit(str(exc))
            if limit is None:
                raise RuntimeError(f"Horizons query failed for {body!r} ({body_id!r}).") from exc
            side, edge = limit
            clamped_start, clamped_end = _clamp_to_grid(
                requested_start, requested_end, seconds, side, edge
            )
            if clamped_start is None or clamped_start > clamped_end:
                reason = f"outside its ephemeris coverage, which {'starts' if side == 'start' else 'ends'} {edge:%Y-%m-%d %H:%M} TDB"
                if notes is None:
                    raise RuntimeError(f"Horizons has no ephemeris for {body!r} {reason}.") from exc
                logging.info("Excluding %s: %s", body, reason)
                notes[body] = f"excluded: {reason}"
                continue
            try:
                coord = get_horizons_coord(
                    body_id,
                    {"start": clamped_start.isoformat(), "stop": clamped_end.isoformat(), "step": step},
                )
            except Exception as retry:
                raise RuntimeError(f"Horizons query failed for {body!r} ({body_id!r}).") from retry
            if notes is not None:
                notes.setdefault(
                    body,
                    f"truncated: kept {clamped_start:%Y-%m-%d %H:%M} to {clamped_end:%Y-%m-%d %H:%M}, "
                    f"the part within its ephemeris coverage",
                )

        try:
            trajectories[body] = coord.transform_to(HeliocentricInertial())
        except Exception as exc:
            raise RuntimeError(f"Could not transform Horizons coordinates for {body!r} to HCI.") from exc

    return trajectories
