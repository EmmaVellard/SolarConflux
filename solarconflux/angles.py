"""Angular helpers for heliocentric longitude comparisons."""

from __future__ import annotations

import math

TAU = 2.0 * math.pi


def normalize_angle_rad(angle_rad: float) -> float:
    """Return an angle in radians normalized to the interval [0, 2 pi)."""
    angle = float(angle_rad)
    if not math.isfinite(angle):
        raise ValueError("Angle must be finite.")
    return angle % TAU


def angular_separation_rad(angle1_rad: float, angle2_rad: float) -> float:
    """Return the smallest circular separation between two angles in radians."""
    angle1 = normalize_angle_rad(angle1_rad)
    angle2 = normalize_angle_rad(angle2_rad)
    return abs((angle1 - angle2 + math.pi) % TAU - math.pi)


def target_separation_rad(angle_rad: float) -> float:
    """Return the unsigned circular separation represented by an angle."""
    normalized = normalize_angle_rad(angle_rad)
    return min(normalized, TAU - normalized)


def degrees_to_radians(angle_degrees: float, name: str = "angle") -> float:
    """Convert a finite angle from degrees to radians."""
    angle = float(angle_degrees)
    if not math.isfinite(angle):
        raise ValueError(f"{name} must be finite.")
    return math.radians(angle)


def radians_to_degrees(angle_rad: float) -> float:
    """Convert a finite angle from radians to degrees."""
    angle = float(angle_rad)
    if not math.isfinite(angle):
        raise ValueError("Angle must be finite.")
    return math.degrees(angle)
