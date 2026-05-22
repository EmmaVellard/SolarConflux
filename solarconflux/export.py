"""CSV and metadata export helpers."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple

from .angles import radians_to_degrees

CSV_COLUMNS = [
    "event_id",
    "start_time",
    "end_time",
    "duration_hours",
    "duration_days",
    "geometry",
    "bodies",
    "number_of_bodies",
    "latitude_tolerance_deg",
    "latitude_span_deg",
    "tolerance_deg",
    "cone_width_deg",
    "arbitrary_angle_deg",
    "solar_wind_speed_km_s",
]


def save_match(
    matching_entries: Mapping[str, Iterable[Tuple[str, str, List[str]]]],
    save_base_path: object,
    parameters: Optional[Mapping[str, Any]] = None,
) -> Path:
    """Save matching entries for all geometries to one CSV file.

    Returns the written CSV path. Empty match sets still produce a predictable
    CSV with headers under ``solarconflux_results``.
    """
    parameters = parameters or {}
    base_path = Path(save_base_path)
    base_path.mkdir(parents=True, exist_ok=True)

    rows = _flatten_entries(matching_entries)
    folder = _output_folder_name(rows)
    output_dir = base_path / folder
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{folder}.csv"
    with csv_path.open(mode="w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for event_id, (start, end, geometry, bodies, latitude_span_deg) in enumerate(rows, start=1):
            writer.writerow(_csv_row(event_id, start, end, geometry, bodies, latitude_span_deg, parameters))

    return csv_path


def save_run_metadata(
    output_dir: object,
    parameters: Mapping[str, Any],
    body_list: Iterable[str],
    horizons_ids: Optional[Mapping[str, Any]] = None,
    package_version: str = "0.1.0",
    output_files: Optional[Iterable[object]] = None,
) -> Path:
    """Save a JSON metadata file describing a SolarConflux run."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    generated_output_filenames = sorted(Path(file_path).name for file_path in output_files or [])
    metadata: MutableMapping[str, Any] = {
        "package_version": package_version,
        "input_parameters": dict(parameters),
        "body_list": list(body_list),
        "horizons_ids": dict(horizons_ids or {}),
        "generated_output_filenames": generated_output_filenames,
        "assumptions": [
            "Heliocentric geometries use spherical longitudes in the selected frame.",
            "Longitude comparisons use circular angular separation.",
            "Parker spiral matching uses a ballistic source-surface footpoint approximation.",
            "SolarConflux is not a full heliospheric MHD model.",
        ],
    }
    metadata_path = path / "run_metadata.json"
    with metadata_path.open("w") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
    return metadata_path


def _flatten_entries(
    matching_entries: Mapping[str, Iterable[Tuple[str, str, List[str]]]]
) -> List[Tuple[str, str, str, List[str], Any]]:
    combined: List[Tuple[str, str, str, List[str], Any]] = []
    for geometry, entries in matching_entries.items():
        for entry in entries:
            start, end, bodies = entry
            combined.append((start, end, geometry, list(bodies), getattr(entry, "latitude_span_deg", "")))
    return sorted(combined, key=lambda row: row[0])


def _output_folder_name(rows: List[Tuple[str, str, str, List[str], Any]]) -> str:
    if not rows:
        return "solarconflux_results"
    return f"{rows[0][0][:10]}_to_{rows[-1][1][:10]}"


def _csv_row(
    event_id: int,
    start: str,
    end: str,
    geometry: str,
    bodies: List[str],
    latitude_span_deg: Any,
    parameters: Mapping[str, Any],
) -> Dict[str, Any]:
    duration_hours = _duration_hours(start, end)
    return {
        "event_id": event_id,
        "start_time": start,
        "end_time": end,
        "duration_hours": duration_hours,
        "duration_days": _duration_days(duration_hours),
        "geometry": geometry,
        "bodies": ";".join(bodies),
        "number_of_bodies": len(bodies),
        "latitude_tolerance_deg": parameters.get("latitude_tolerance_deg", ""),
        "latitude_span_deg": _format_optional_float(latitude_span_deg),
        "tolerance_deg": _parameter_degrees(parameters, "tolerance"),
        "cone_width_deg": _parameter_degrees(parameters, "cone_width"),
        "arbitrary_angle_deg": parameters.get("arbitrary_angle_degrees", ""),
        "solar_wind_speed_km_s": _solar_wind_speed_km_s(parameters),
    }


def _duration_hours(start: str, end: str) -> str:
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return ""
    duration = end_dt - start_dt
    return f"{duration.total_seconds() / 3600.0:.6g}"


def _duration_days(duration_hours: str) -> str:
    if not duration_hours:
        return ""
    return f"{float(duration_hours) / 24.0:.6g}"


def _format_optional_float(value: Any) -> Any:
    if value is None or value == "":
        return ""
    return f"{float(value):.6g}"


def _parameter_degrees(parameters: Mapping[str, Any], key: str) -> Any:
    degree_key = f"{key}_degrees"
    if degree_key in parameters and parameters[degree_key] is not None:
        return parameters[degree_key]
    radian_key = f"{key}_radians"
    if radian_key in parameters and parameters[radian_key] is not None:
        return f"{radians_to_degrees(float(parameters[radian_key])):.6g}"
    if key in parameters and parameters[key] is not None:
        return parameters[key]
    return ""


def _solar_wind_speed_km_s(parameters: Mapping[str, Any]) -> Any:
    if "solar_wind_speed_km_s" in parameters and parameters["solar_wind_speed_km_s"] is not None:
        return parameters["solar_wind_speed_km_s"]
    if "u_sw" in parameters and parameters["u_sw"] is not None:
        return f"{float(parameters['u_sw']) / 1000.0:.6g}"
    return ""
