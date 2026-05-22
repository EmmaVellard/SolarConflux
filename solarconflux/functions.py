"""Backward-compatible public helpers for SolarConflux."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from .bodies import get_infos, horizons_ids_for_bodies, validate_body_names
from .export import save_match, save_run_metadata
from .geometries import Geometry
from .plotting import coord_to_polar, save_plot
from .trajectories import get_info, get_trajectories
from .validation import (
    angle_to_radians as _angle_to_radians,
    normalize_geometry_choices,
    validate_optional_latitude_tolerance_degrees,
    validate_non_negative_angle,
    validate_positive_angle,
    validate_solar_wind_speed_mps,
)


def matching_dates(
    geometry_choices: Iterable[str],
    spacecraft_names: Iterable[str],
    trajectories: Mapping[str, object],
    frame: object = None,
    cone_width: float = 10.0,
    tolerance: float = 10.0,
    arbitrary_angle: Optional[float] = None,
    latitude_tolerance_deg: Optional[float] = None,
    u_sw: float = 400e3,
    angle_unit: str = "deg",
    verbose: bool = True,
) -> Dict[str, object]:
    """Find matching time ranges for requested geometries.

    User-facing angle inputs default to degrees. Set ``angle_unit='rad'`` for
    backward-compatible radian inputs.
    """
    bodies = validate_body_names(spacecraft_names)
    modes = normalize_geometry_choices(geometry_choices)
    cone_width_rad = validate_positive_angle(
        _angle_to_radians(cone_width, angle_unit, "cone_width"),
        "cone_width",
    )
    tolerance_rad = validate_non_negative_angle(
        _angle_to_radians(tolerance, angle_unit, "tolerance"),
        "tolerance",
    )
    arbitrary_angle_rad = None
    if "arbitrary" in modes:
        arbitrary_angle_rad = validate_non_negative_angle(
            _angle_to_radians(arbitrary_angle, angle_unit, "arbitrary_angle"),
            "arbitrary_angle",
        )
    latitude_tolerance_degrees = validate_optional_latitude_tolerance_degrees(latitude_tolerance_deg)
    latitude_tolerance_rad = (
        None
        if latitude_tolerance_degrees is None
        else _angle_to_radians(latitude_tolerance_degrees, "deg", "latitude_tolerance_deg")
    )

    speed_mps = validate_solar_wind_speed_mps(u_sw)
    geometry = Geometry(
        bodies,
        trajectories,
        frame,
        cone_width_rad,
        tolerance_rad,
        latitude_tolerance=latitude_tolerance_rad,
    )

    all_matching_entries: Dict[str, object] = {}
    for mode in modes:
        matches = geometry.check_geometry(
            mode=mode,
            arbitrary_angle=arbitrary_angle_rad,
            u_sw=speed_mps,
        )
        if matches:
            all_matching_entries[mode] = matches
        if verbose:
            print(f"{mode}: {len(matches)} matches found." if matches else f"{mode}: no matches.")

    return all_matching_entries


def build_run_parameters(
    cone_width_degrees: float = 10.0,
    tolerance_degrees: float = 10.0,
    arbitrary_angle_degrees: Optional[float] = None,
    latitude_tolerance_deg: Optional[float] = None,
    solar_wind_speed_km_s: float = 400.0,
) -> Dict[str, Any]:
    """Return a metadata-friendly parameter dictionary."""
    return {
        "cone_width_degrees": cone_width_degrees,
        "tolerance_degrees": tolerance_degrees,
        "arbitrary_angle_degrees": arbitrary_angle_degrees,
        "latitude_tolerance_deg": latitude_tolerance_deg,
        "solar_wind_speed_km_s": solar_wind_speed_km_s,
    }


__all__ = [
    "Geometry",
    "build_run_parameters",
    "coord_to_polar",
    "get_info",
    "get_infos",
    "get_trajectories",
    "horizons_ids_for_bodies",
    "matching_dates",
    "save_match",
    "save_plot",
    "save_run_metadata",
]
