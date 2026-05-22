"""Geometry detection for heliocentric spacecraft and planet trajectories.

The calculations in this module are intentionally approximate geometric
screening tools. They compare heliocentric longitudes, optional latitudes,
and simple Parker-spiral footpoint estimates. They are not a heliospheric
plasma model or an MHD connectivity calculation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .angles import angular_separation_rad, target_separation_rad
from .events import MatchEntry, format_timestamp
from .validation import (
    normalize_geometry_choices,
    validate_non_negative_angle,
    validate_positive_angle,
    validate_solar_wind_speed_mps,
)


@dataclass(frozen=True)
class TrajectoryPoint:
    """A lightweight trajectory point for tests and scripted use.

    Parameters are heliocentric spherical coordinates in radians and km.
    Real Astropy/SunPy coordinates are also accepted by :class:`Geometry`.
    """

    time: datetime
    lon_rad: float
    lat_rad: float = 0.0
    radius_km: float = 1.0


@dataclass(frozen=True)
class BodyState:
    """A normalized body state at one time step."""

    name: str
    time: object
    lon_rad: float
    lat_rad: Optional[float]
    radius_km: float


class Geometry:
    """Detect supported geometric alignments in heliocentric trajectories."""

    def __init__(
        self,
        spacecraft_names: Iterable[str],
        trajectories: Mapping[str, Sequence[object]],
        frame: object = None,
        cone_width: float = math.radians(10.0),
        tolerance: float = math.radians(10.0),
        solar_rotation_period: float = 25.38,
        parker_tolerance: float = math.radians(5.0),
        source_surface_radius_km: float = 2.5 * 696000.0,
        latitude_tolerance: Optional[float] = None,
    ) -> None:
        self.spacecraft_names = tuple(spacecraft_names)
        self.trajectories = dict(trajectories)
        self.frame = frame
        self.cone_width = validate_positive_angle(cone_width, "cone_width")
        self.tolerance = validate_non_negative_angle(tolerance, "tolerance")
        self.tolerance_parker = validate_non_negative_angle(parker_tolerance, "parker_tolerance")
        self.latitude_tolerance = (
            None
            if latitude_tolerance is None
            else validate_non_negative_angle(latitude_tolerance, "latitude_tolerance")
        )
        self.source_surface_radius = float(source_surface_radius_km)

        if solar_rotation_period <= 0 or not math.isfinite(float(solar_rotation_period)):
            raise ValueError("solar_rotation_period must be positive and finite.")
        self.solar_rotation_rate = 2.0 * math.pi / (float(solar_rotation_period) * 24.0 * 3600.0)

        self._validate_trajectories()
        self.states = self.calculate_states()
        self.angles, self.latitudes = self.calculate_angles()

    def _validate_trajectories(self) -> None:
        if not self.trajectories:
            raise ValueError("At least one trajectory is required.")

        missing = [name for name in self.spacecraft_names if name not in self.trajectories]
        if missing:
            raise ValueError("Missing trajectories for: " + ", ".join(missing) + ".")

        lengths = {name: len(values) for name, values in self.trajectories.items()}
        empty = [name for name, length in lengths.items() if length == 0]
        if empty:
            raise ValueError("Trajectories must not be empty: " + ", ".join(empty) + ".")

        unique_lengths = set(lengths.values())
        if len(unique_lengths) != 1:
            details = ", ".join(f"{name}={length}" for name, length in lengths.items())
            raise ValueError("All trajectories must have the same number of time steps: " + details + ".")

    def calculate_states(self) -> List[List[BodyState]]:
        """Return normalized body states for each time step."""
        num_steps = len(next(iter(self.trajectories.values())))
        states: List[List[BodyState]] = []

        for step in range(num_steps):
            step_states = []
            for name, trajectory in self.trajectories.items():
                step_states.append(self._extract_state(name, trajectory[step]))
            states.append(step_states)

        return states

    def calculate_angles(self) -> Tuple[List[List[float]], List[List[float]]]:
        """Return longitude and latitude arrays in radians."""
        angles = [[state.lon_rad for state in step_states] for step_states in self.states]
        latitudes = [[state.lat_rad for state in step_states] for step_states in self.states]
        return angles, latitudes

    def parker_spiral_function(self, r_km: float, lon_rad: float, u_sw_mps: float) -> float:
        """Estimate Parker source-surface footpoint longitude.

        This preserves the original SolarConflux convention:

        ``phi_source = phi_body + omega_sun * (r_body - r_source_surface) / u_sw``

        with distances converted to meters, solar wind speed in m/s, and a
        default sidereal Carrington-like rotation period of 25.38 days. The
        result is a ballistic backmapping approximation and should not be read
        as a full magnetic connectivity model.
        """
        speed = validate_solar_wind_speed_mps(u_sw_mps)
        r_m = float(r_km) * 1e3
        r_ss_m = self.source_surface_radius * 1e3
        phi_0 = float(lon_rad) + (self.solar_rotation_rate / speed) * (r_m - r_ss_m)
        return phi_0 % (2.0 * math.pi)

    def check_geometry(
        self,
        mode: str = "opposition",
        arbitrary_angle: Optional[float] = None,
        u_sw: float = 400e3,
    ) -> List[MatchEntry]:
        """Return grouped events matching one geometry mode.

        ``arbitrary_angle`` is interpreted in radians here. Public helper
        functions and the CLI accept degrees by default and convert before
        calling this class.
        """
        normalized_mode = normalize_geometry_choices([mode])[0]
        if normalized_mode == "arbitrary":
            if arbitrary_angle is None:
                raise ValueError("arbitrary_angle is required when mode='arbitrary'.")
            arbitrary_angle = validate_non_negative_angle(arbitrary_angle, "arbitrary_angle")
        if normalized_mode in {"parker", "coneparker"}:
            validate_solar_wind_speed_mps(u_sw)

        active_groups: Dict[Tuple[str, ...], Tuple[object, object, Optional[float]]] = {}
        matching_entries: List[MatchEntry] = []
        for step_states in self.states:
            timestamp = step_states[0].time
            groups = self._groups_for_step(step_states, normalized_mode, arbitrary_angle, u_sw)
            new_active_groups: Dict[Tuple[str, ...], Tuple[object, object, Optional[float]]] = {}

            for group, latitude_span_deg in groups:
                if group in active_groups:
                    start_time, _, previous_span = active_groups[group]
                    new_active_groups[group] = (
                        start_time,
                        timestamp,
                        _max_optional(previous_span, latitude_span_deg),
                    )
                else:
                    new_active_groups[group] = (timestamp, timestamp, latitude_span_deg)

            for ended_group, (start_time, end_time, latitude_span_deg) in active_groups.items():
                if ended_group not in new_active_groups:
                    matching_entries.append(
                        MatchEntry(
                            format_timestamp(start_time),
                            format_timestamp(end_time),
                            list(ended_group),
                            latitude_span_deg=latitude_span_deg,
                        )
                    )

            active_groups = new_active_groups

        for group, (start_time, end_time, latitude_span_deg) in active_groups.items():
            matching_entries.append(
                MatchEntry(
                    format_timestamp(start_time),
                    format_timestamp(end_time),
                    list(group),
                    latitude_span_deg=latitude_span_deg,
                )
            )

        return matching_entries

    def _groups_for_step(
        self,
        step_states: Sequence[BodyState],
        mode: str,
        arbitrary_angle: Optional[float],
        u_sw: float,
    ) -> List[Tuple[Tuple[str, ...], Optional[float]]]:
        groups: Dict[Tuple[str, ...], Optional[float]] = {}
        state_by_name = {state.name: state for state in step_states}

        for state1 in step_states:
            group = {state1.name}

            for state2 in step_states:
                if state1.name == state2.name:
                    continue
                if self._condition_matches(state1, state2, mode, arbitrary_angle, u_sw):
                    group.add(state2.name)

            if len(group) > 1 and not (len(group) == 2 and "Sun" in group):
                candidate_group = tuple(sorted(group))
                latitude_span_deg = self._latitude_span_degrees(state_by_name, candidate_group)
                if self._passes_latitude_filter(latitude_span_deg):
                    groups[candidate_group] = _max_optional(groups.get(candidate_group), latitude_span_deg)

        return list(groups.items())

    def _condition_matches(
        self,
        state1: BodyState,
        state2: BodyState,
        mode: str,
        arbitrary_angle: Optional[float],
        u_sw: float,
    ) -> bool:
        lon_sep = angular_separation_rad(state1.lon_rad, state2.lon_rad)

        if mode == "opposition":
            return abs(lon_sep - math.pi) <= self.tolerance

        if mode == "cone":
            return lon_sep <= self.cone_width

        if mode == "quadrature":
            return abs(lon_sep - (math.pi / 2.0)) <= self.tolerance

        if mode == "arbitrary":
            target = target_separation_rad(float(arbitrary_angle))
            return abs(lon_sep - target) <= self.tolerance

        if mode == "parker":
            return self._parker_matches(state1, state2, u_sw)

        if mode == "coneparker":
            return lon_sep <= self.cone_width and self._parker_matches(state1, state2, u_sw)

        return False

    def _parker_matches(self, state1: BodyState, state2: BodyState, u_sw: float) -> bool:
        phi0_1 = self.parker_spiral_function(state1.radius_km, state1.lon_rad, u_sw)
        phi0_2 = self.parker_spiral_function(state2.radius_km, state2.lon_rad, u_sw)
        footpoint_close = angular_separation_rad(phi0_1, phi0_2) <= self.tolerance_parker
        latitude_close = abs(_require_latitude(state1) - _require_latitude(state2)) <= self.tolerance
        return footpoint_close and latitude_close

    def _latitude_span_degrees(
        self,
        state_by_name: Mapping[str, BodyState],
        group: Tuple[str, ...],
    ) -> Optional[float]:
        latitudes = []
        for name in group:
            latitude = state_by_name[name].lat_rad
            if latitude is None or not math.isfinite(latitude):
                if self.latitude_tolerance is not None:
                    raise ValueError(
                        "Latitude data are missing or nonfinite for "
                        f"{name}; cannot apply latitude_tolerance_deg."
                    )
                return None
            latitudes.append(latitude)
        if not latitudes:
            return None
        return math.degrees(max(latitudes) - min(latitudes))

    def _passes_latitude_filter(self, latitude_span_deg: Optional[float]) -> bool:
        if self.latitude_tolerance is None:
            return True
        if latitude_span_deg is None:
            raise ValueError("Latitude data are required when latitude_tolerance_deg is set.")
        return latitude_span_deg <= math.degrees(self.latitude_tolerance) + 1e-12

    def _extract_state(self, name: str, coordinate: object) -> BodyState:
        if isinstance(coordinate, TrajectoryPoint):
            return BodyState(
                name=name,
                time=coordinate.time,
                lon_rad=coordinate.lon_rad,
                lat_rad=coordinate.lat_rad,
                radius_km=coordinate.radius_km,
            )

        transformed = coordinate
        if self.frame is not None and hasattr(coordinate, "transform_to"):
            transformed = coordinate.transform_to(self.frame)

        spherical = getattr(transformed, "spherical", None)
        if spherical is None:
            raise TypeError(
                f"Trajectory point for {name} must be a TrajectoryPoint or expose a spherical coordinate."
            )

        lon_rad = _angle_to_rad(getattr(spherical, "lon"))
        lat = getattr(spherical, "lat", None)
        lat_rad = None if lat is None else _angle_to_rad(lat)
        radius_km = _distance_to_km(getattr(spherical, "distance"))
        timestamp = _coordinate_time(transformed)
        return BodyState(name=name, time=timestamp, lon_rad=lon_rad, lat_rad=lat_rad, radius_km=radius_km)


def _angle_to_rad(value: object) -> float:
    if hasattr(value, "to_value"):
        return float(value.to_value("rad"))
    if hasattr(value, "rad"):
        return float(value.rad)
    return float(value)


def _distance_to_km(value: object) -> float:
    if hasattr(value, "to_value"):
        return float(value.to_value("km"))
    if hasattr(value, "to"):
        return float(value.to("km").value)
    if hasattr(value, "value"):
        return float(value.value)
    return float(value)


def _coordinate_time(value: object) -> object:
    obstime = getattr(value, "obstime", None)
    if obstime is not None:
        if hasattr(obstime, "datetime"):
            return obstime.datetime
        return obstime
    time_value = getattr(value, "time", None)
    if time_value is not None:
        return time_value
    raise TypeError("Trajectory point must expose an observation time.")


def _max_optional(value1: Optional[float], value2: Optional[float]) -> Optional[float]:
    if value1 is None:
        return value2
    if value2 is None:
        return value1
    return max(value1, value2)


def _require_latitude(state: BodyState) -> float:
    if state.lat_rad is None or not math.isfinite(state.lat_rad):
        raise ValueError(f"Latitude data are missing or nonfinite for {state.name}.")
    return state.lat_rad
