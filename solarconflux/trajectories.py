"""Trajectory retrieval from JPL Horizons via SunPy."""

from __future__ import annotations

from typing import Dict, Iterable

from .bodies import get_infos, validate_body_names
from .validation import validate_date_range, validate_step


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
) -> Dict[str, object]:
    """Fetch and convert trajectories to the Heliocentric Inertial frame.

    This function requires SunPy, Astropy, and Astroquery at runtime. Unit tests
    can use :class:`solarconflux.geometries.TrajectoryPoint` instead of live
    Horizons queries.
    """
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

    for body in bodies:
        body_id = body_info[body]["id"]
        try:
            coord = get_horizons_coord(
                body_id,
                {"start": start_time, "stop": end_time, "step": step},
            )
        except Exception as exc:
            raise RuntimeError(f"Horizons query failed for {body!r} ({body_id!r}).") from exc

        try:
            trajectories[body] = coord.transform_to(HeliocentricInertial())
        except Exception as exc:
            raise RuntimeError(f"Could not transform Horizons coordinates for {body!r} to HCI.") from exc

    return trajectories
