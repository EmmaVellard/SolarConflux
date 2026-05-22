"""Input validation for public SolarConflux APIs."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Iterable, List, Union

from .angles import degrees_to_radians

SUPPORTED_GEOMETRIES = (
    "opposition",
    "cone",
    "quadrature",
    "arbitrary",
    "parker",
    "coneparker",
)

_GEOMETRY_ALIASES = {
    "cone-parker": "coneparker",
    "cone_parker": "coneparker",
    "cone parker": "coneparker",
    "parker-cone": "coneparker",
}

_STEP_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours|d|day|days)\s*$")


def parse_datetime(value: object, name: str) -> datetime:
    """Parse a date/time value using Python's ISO-like datetime parser."""
    if isinstance(value, datetime):
        return value
    if value is None:
        raise ValueError(f"{name} is required.")

    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required.")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a valid ISO-like date/time, for example 2025-01-01 or 2025-01-01 12:00."
        ) from exc


def validate_date_range(start_time: object, end_time: object) -> None:
    """Validate that start and end times parse and are ordered."""
    start = parse_datetime(start_time, "start_time")
    end = parse_datetime(end_time, "end_time")
    if start >= end:
        raise ValueError("start_time must be earlier than end_time.")


def validate_step(step: object) -> str:
    """Validate a positive Horizons-style time step such as 60m, 1h, or 1d."""
    if step is None:
        raise ValueError("step is required.")
    text = str(step).strip()
    match = _STEP_PATTERN.match(text)
    if not match:
        raise ValueError("step must be a positive value with units, for example 60m, 1h, or 1d.")
    value = float(match.group(1))
    if value <= 0 or not math.isfinite(value):
        raise ValueError("step must be positive and finite.")
    return text


def normalize_geometry_choices(choices: Union[str, Iterable[str]]) -> List[str]:
    """Normalize and validate requested geometry mode names."""
    if isinstance(choices, str):
        raw_choices = choices.split(",")
    else:
        raw_choices = list(choices)

    normalized: List[str] = []
    seen = set()
    for choice in raw_choices:
        mode = str(choice).strip().lower()
        if not mode:
            continue
        mode = _GEOMETRY_ALIASES.get(mode, mode)
        if mode not in SUPPORTED_GEOMETRIES:
            supported = ", ".join(SUPPORTED_GEOMETRIES)
            raise ValueError(f"Unsupported geometry mode '{choice}'. Supported modes are: {supported}.")
        if mode not in seen:
            normalized.append(mode)
            seen.add(mode)

    if not normalized:
        raise ValueError("At least one geometry mode must be provided.")
    return normalized


def angle_to_radians(value: object, unit: str, name: str) -> float:
    """Convert an angle to radians after validating the unit name."""
    if value is None:
        raise ValueError(f"{name} is required.")
    normalized_unit = unit.strip().lower()
    if normalized_unit in {"deg", "degree", "degrees"}:
        angle_rad = degrees_to_radians(float(value), name)
    elif normalized_unit in {"rad", "radian", "radians"}:
        angle_rad = float(value)
        if not math.isfinite(angle_rad):
            raise ValueError(f"{name} must be finite.")
    else:
        raise ValueError("angle_unit must be 'deg' or 'rad'.")
    return angle_rad


def validate_non_negative_angle(angle_rad: float, name: str) -> float:
    """Validate a finite non-negative angle in radians."""
    angle = float(angle_rad)
    if not math.isfinite(angle):
        raise ValueError(f"{name} must be finite.")
    if angle < 0:
        raise ValueError(f"{name} must be non-negative.")
    return angle


def validate_positive_angle(angle_rad: float, name: str) -> float:
    """Validate a finite positive angle in radians."""
    angle = validate_non_negative_angle(angle_rad, name)
    if angle <= 0:
        raise ValueError(f"{name} must be positive.")
    return angle


def validate_solar_wind_speed_mps(speed_mps: object) -> float:
    """Validate solar wind speed in meters per second."""
    speed = float(speed_mps)
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("Solar wind speed must be positive and finite.")
    return speed
