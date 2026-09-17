"""Portable JSON boundary shared by the CLI and the static browser GUI."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .geometries import Geometry, TrajectoryPoint
from .events import format_timestamp
from .validation import parse_datetime

SCHEMA = "solarconflux.trajectories.v1"


_SOURCE_LABELS = {
    "horizons": "JPL Horizons via SunPy; transformed to HCI",
    "spice": "SPICE kernels via spiceypy; transformed to HCI",
    "prefer-spice": "SPICE kernels where available, otherwise JPL Horizons; transformed to HCI",
}


def trajectory_bundle(trajectories, start_time, end_time, step, source="horizons", provenance=None, notes=None):
    geometry = Geometry(trajectories.keys(), trajectories)
    payload = {
        "schema": SCHEMA, "frame": "HeliocentricInertial", "time_scale": "UTC",
        "source": _SOURCE_LABELS[source],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "time_precision": "UTC timestamps rounded to the nearest second after HCI conversion.",
        "requested_start": str(start_time), "requested_end": str(end_time), "step": step,
        "trajectories": {name: [] for name in trajectories},
    }
    # Recorded whenever bodies can come from different backends, so a mixed run states which
    # body came from where rather than leaving the reader to guess.
    if provenance:
        payload["body_sources"] = {name: provenance[name] for name in trajectories if name in provenance}
    # Explains any body truncated to its ephemeris coverage or left out of the run, so a
    # short or missing trajectory is never silent.
    if notes:
        payload["coverage_notes"] = dict(notes)
    for states in geometry.states:
        for s in states:
            payload["trajectories"][s.name].append({
                "time": format_timestamp(s.time).replace(" ", "T") + "Z",
                "lon_deg": math.degrees(s.lon_rad), "lat_deg": math.degrees(s.lat_rad),
                "radius_km": s.radius_km,
            })
    return payload


def save_trajectory_bundle(trajectories, path, start_time, end_time, step, source="horizons", provenance=None, notes=None):
    payload = trajectory_bundle(trajectories, start_time, end_time, step, source=source, provenance=provenance, notes=notes)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    return target


def load_bundle(payload):
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("Choose a SolarConflux trajectory JSON exported with --export-trajectories.")
    if payload.get("frame") != "HeliocentricInertial" or payload.get("time_scale") != "UTC":
        raise ValueError("Trajectories must declare the HeliocentricInertial frame and UTC time scale.")
    raw = payload.get("trajectories")
    if not isinstance(raw, dict) or not 2 <= len(raw) <= 17:
        raise ValueError("A trajectory file must contain between 2 and 17 supported bodies.")
    from .bodies import validate_body_names
    validate_body_names(raw)
    trajectories = {}
    for name, points in raw.items():
        if not isinstance(points, list) or not 1 <= len(points) <= 20000:
            raise ValueError("Each body needs 1 to 20,000 samples.")
        try:
            trajectories[name] = [TrajectoryPoint(
                parse_datetime(p["time"], "sample time"),
                math.radians(float(p["lon_deg"])), math.radians(float(p["lat_deg"])),
                float(p["radius_km"]),
            ) for p in points]
        except (KeyError, TypeError, OverflowError) as exc:
            raise ValueError("Each sample needs time, lon_deg, lat_deg, and radius_km.") from exc
    Geometry(trajectories.keys(), trajectories)
    # Bodies may cover different intervals, because a mission's ephemeris can start or end
    # inside the requested window. What must still hold is that every body samples the same
    # uniform cadence, which is what rejects stray or misaligned timestamps now that lengths
    # are allowed to differ.
    cadences = set()
    for name, points in trajectories.items():
        times = [p.time for p in points]
        if len(times) < 3:
            continue
        cadence = (times[1] - times[0]).total_seconds()
        if any(abs((b - a).total_seconds() - cadence) > 1 for a, b in zip(times, times[1:])):
            raise ValueError(
                f"Samples for {name} must have a uniform cadence; split files containing gaps before screening."
            )
        cadences.add(round(cadence))
    if len(cadences) > 1:
        raise ValueError("Every body must be sampled at the same cadence: " + ", ".join(
            f"{name}={round((points[1].time - points[0].time).total_seconds())}s"
            for name, points in trajectories.items() if len(points) > 1) + ".")
    return trajectories


def screen_bundle(payload, config):
    """Run the unchanged public screening/export API on selected imported samples."""
    from .functions import matching_dates, build_run_parameters
    from .export import _csv_row, CSV_COLUMNS
    from .bodies import validate_body_names
    import csv
    import io
    trajectories = load_bundle(payload)
    bodies = validate_body_names(config["bodies"])
    if len(bodies) < 2 or any(b not in trajectories for b in bodies):
        raise ValueError("Select at least two bodies available in this dataset.")
    start = parse_datetime(config["start"], "start")
    end = parse_datetime(config["end"], "end")
    if start > end:
        raise ValueError("Start must be before or equal to end.")
    # Compare against the widest span in the file: an individual body may be truncated to its
    # own ephemeris coverage, so the first body is not necessarily representative.
    first = min(points[0].time for points in trajectories.values())
    last = max(points[-1].time for points in trajectories.values())
    if start < first or end > last:
        raise ValueError("The date range must stay within the imported data coverage.")
    available = max(trajectories.values(), key=len)
    selected = {b: [p for p in trajectories[b] if start <= p.time <= end] for b in bodies}
    parameters = build_run_parameters(config["cone"], config["tolerance"], config["angle"], config["latitude"], config["speed"])
    matches = matching_dates(config["modes"], bodies, selected, cone_width=config["cone"], tolerance=config["tolerance"], arbitrary_angle=config["angle"], latitude_tolerance_deg=config["latitude"], u_sw=config["speed"] * 1000, verbose=False)
    rows = []
    for mode, entries in matches.items():
        for e in entries:
            rows.append(_csv_row(0, e.start_time, e.end_time, mode, e.group, e.latitude_span_deg, parameters))
    rows.sort(key=lambda r: (r["start_time"], r["geometry"], r["bodies"]))
    for i, row in enumerate(rows, 1):
        row["event_id"] = i
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return {"events": rows, "csv": stream.getvalue(), "metadata": {
        "package_version": "0.1.0", "engine": "SolarConflux Python / browser",
        "input_parameters": {**parameters, "start_time": config["start"], "end_time": config["end"], "geometries": config["modes"]},
        "body_list": bodies, "frame": "HeliocentricInertial", "time_scale": "UTC",
        "source": payload.get("source", "User-provided; provenance unverified"),
        "retrieved_at": payload.get("retrieved_at"), "sample_count_per_body": len(selected[bodies[0]]),
        "cadence_seconds": (available[1].time - available[0].time).total_seconds() if len(available) > 1 else None,
        "parker_tolerance_degrees": 5, "solar_rotation_period_days": 25.38,
        "source_surface_radius_km": 1740000,
        "assumptions": ["Approximate geometric screening, not validated magnetic connectivity.", "Groups share an anchor body; not every pair must match.", "Event bounds are matching sample times, not interpolated crossings."],
    }}
