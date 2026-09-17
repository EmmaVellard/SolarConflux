#!/usr/bin/env python
"""Compare the Horizons and SPICE trajectory backends body by body.

Both backends are asked for the same bodies, interval and step, and the residuals between
them are reported in the Heliocentric Inertial frame. Exits non-zero if any body exceeds
its tolerance, so this doubles as a regression check.

Example:
    python scripts/compare_sources.py --bodies Earth,Venus,Mars --start-time 2025-01-01 \
        --end-time 2025-01-05 --step 1d
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run against this checkout rather than any copy installed in site-packages.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Bodies whose ephemeris both backends ultimately take from the same source should agree to
# numerical precision; a residual there means the conversion is wrong.
PLANETS = {"Earth", "Venus", "Mars", "Jupiter"}
PLANET_TOLERANCE_KM = 1.0
SPACECRAFT_TOLERANCE_KM = 50.0

# de440s.bsp carries no body centre for Mars or Jupiter, so the SPICE backend reads their
# system barycentres while Horizons reports the body centre. The offset is expected and
# bounded by the satellite systems: ~0.2 m for Mars, ~230 km for Jupiter.
BARYCENTRE_TOLERANCE_KM = {"Jupiter": 300.0}

# Bodies where the public archive is a genuinely different product from the ephemeris
# Horizons serves, so a residual is real data disagreement rather than a conversion error.
# What matters for alignment screening is the angular effect, so these are held to an
# angular bound instead of a distance one.
ARCHIVE_DIFFERENCES = {
    "Stereo-A": (
        "NAIF's merged SPK is lower fidelity than the STEREO Science Center ephemeris "
        "Horizons serves, and is predicted rather than reconstructed after 2015"
    ),
}
# 0.02 deg, more than two orders of magnitude below this package's screening tolerances.
ARCHIVE_TOLERANCE_ARCSEC = 72.0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bodies", default="Earth,Venus,Mars,Jupiter", help="Comma-separated body names.")
    parser.add_argument("--start-time", default="2025-01-01")
    parser.add_argument("--end-time", default="2025-01-05")
    parser.add_argument("--step", default="1d")
    args = parser.parse_args(argv)

    import astropy.units as u
    import numpy as np

    from solarconflux.bodies import validate_body_names
    from solarconflux.trajectories import get_trajectories

    bodies = validate_body_names(args.bodies)
    # The Sun is the HCI origin, so Horizons cannot report it as a target.
    bodies = [b for b in bodies if b != "Sun"]
    if not bodies:
        parser.error("Provide at least one body other than the Sun.")

    print(f"Interval {args.start_time} to {args.end_time}, step {args.step}\n")
    header = f"{'Body':<16} {'N':>4} {'max dlon':>11} {'max dlat':>11} {'max dr':>12} {'max sep':>12} {'ang sep':>10}  Verdict"
    print(header)
    print("-" * len(header))

    failures, skipped, compared = [], [], 0
    for body in bodies:
        try:
            spice = get_trajectories([body], args.start_time, args.end_time, args.step, source="spice")[body]
            horizons = get_trajectories([body], args.start_time, args.end_time, args.step, source="horizons")[body]
        except Exception as exc:
            skipped.append(body)
            print(f"{body:<16} {'-':>4} {'-':>11} {'-':>11} {'-':>12} {'-':>12} {'-':>10}  SKIPPED: {exc}")
            continue
        compared += 1

        dlon = max(abs((spice.lon - horizons.lon).to_value(u.arcsec)))
        dlat = max(abs((spice.lat - horizons.lat).to_value(u.arcsec)))
        dr = max(abs((spice.distance - horizons.distance).to_value(u.km)))
        sep_km = max((spice.cartesian - horizons.cartesian).norm().to_value(u.km))
        # atan2 of the cross and dot products, rather than arccos of the dot product: for
        # near-identical vectors arccos loses half its significant digits and bottoms out
        # around 2e-3 arcsec, which is coarser than the agreement being measured.
        a = np.atleast_2d(spice.cartesian.xyz.to_value(u.km).T)
        b = np.atleast_2d(horizons.cartesian.xyz.to_value(u.km).T)
        sep_arcsec = max(np.degrees(np.arctan2(
            np.linalg.norm(np.cross(a, b), axis=-1), np.sum(a * b, axis=-1))) * 3600.0)

        if body in ARCHIVE_DIFFERENCES:
            ok = sep_arcsec <= ARCHIVE_TOLERANCE_ARCSEC
            verdict = "differs (archive)" if ok else f'EXCEEDS {ARCHIVE_TOLERANCE_ARCSEC:g}"'
        else:
            default = PLANET_TOLERANCE_KM if body in PLANETS else SPACECRAFT_TOLERANCE_KM
            tolerance = BARYCENTRE_TOLERANCE_KM.get(body, default)
            ok = sep_km <= tolerance
            if not ok:
                verdict = f"DIFFERS (> {tolerance:g} km)"
            elif body in BARYCENTRE_TOLERANCE_KM:
                verdict = "match (barycentre)"
            else:
                verdict = "match"
        if not ok:
            failures.append(body)

        print(
            f"{body:<16} {len(spice):>4} {dlon:>10.2e}\" {dlat:>10.2e}\" {dr:>9.3e} km "
            f"{sep_km:>9.3e} km {sep_arcsec:>9.2e}\"  {verdict}"
        )

    if any(b in BARYCENTRE_TOLERANCE_KM for b in bodies):
        print("\n(barycentre) SPICE reads the system barycentre; Horizons reports the body centre.")
    for body in bodies:
        if body in ARCHIVE_DIFFERENCES:
            print(f"(archive) {body}: {ARCHIVE_DIFFERENCES[body]}.")
    if skipped:
        print(f"\nSkipped (could not compare): {', '.join(skipped)}")
    if failures:
        print(f"Bodies exceeding tolerance: {', '.join(failures)}")
        return 1
    if not compared:
        print("\nNo bodies could be compared.")
        return 1
    print(f"\nAll {compared} compared bodies agree within tolerance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
