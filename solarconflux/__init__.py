"""
SolarConflux
============

Tool for identifying geometric alignments between spacecraft
around the Sun for coordinated solar observations.
"""

__version__ = "0.1.0"

from .angles import angular_separation_rad, normalize_angle_rad
from .bodies import get_infos, supported_body_names
from .functions import (
    Geometry,
    build_run_parameters,
    coord_to_polar,
    get_info,
    get_trajectories,
    horizons_ids_for_bodies,
    matching_dates,
    save_match,
    save_plot,
    save_run_metadata,
)
from .geometries import TrajectoryPoint

__all__ = [
    "Geometry",
    "TrajectoryPoint",
    "__version__",
    "angular_separation_rad",
    "build_run_parameters",
    "coord_to_polar",
    "get_info",
    "get_infos",
    "get_trajectories",
    "horizons_ids_for_bodies",
    "matching_dates",
    "normalize_angle_rad",
    "save_match",
    "save_plot",
    "save_run_metadata",
    "supported_body_names",
]
