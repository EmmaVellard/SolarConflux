"""Plotting helpers for SolarConflux outputs."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable as IterableABC
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence, Tuple

from .geometries import _distance_to_km, _angle_to_rad


def coord_to_polar(coord: object) -> Tuple[float, float]:
    """Convert a trajectory point or Astropy-like coordinate to lon/radius."""
    if hasattr(coord, "lon_rad") and hasattr(coord, "radius_km"):
        return float(coord.lon_rad), float(coord.radius_km)

    spherical = getattr(coord, "spherical", None)
    if spherical is None:
        raise TypeError("Coordinate must expose spherical lon and distance values.")
    return _angle_to_rad(getattr(spherical, "lon")), _distance_to_km(getattr(spherical, "distance"))


def save_plot(
    matching_trajectories: Mapping[str, Iterable[Tuple[str, str, Iterable[str]]]],
    trajectories: Mapping[str, Iterable[object]],
    save_base_path: object,
    formats: Sequence[str] = ("png",),
) -> List[Path]:
    """Save polar plots of matched spacecraft positions.

    Returns the saved plot paths. ``formats`` defaults to PNG and may include
    other Matplotlib-supported formats such as PDF.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError("Plotting requires matplotlib.") from exc

    if isinstance(formats, str):
        formats = (formats,)
    formats = tuple(_normalize_format(file_format) for file_format in formats)
    colors = ["#1f77b4", "#d62728", "#9467bd", "#17becf", "#2ca02c", "#8c564b", "#bcbd22", "#ff7f0e", "#7f7f7f", "#e377c2"]
    plots_per_file = 15
    saved_paths: List[Path] = []

    all_dates = [(entry[0], entry[1]) for entries in matching_trajectories.values() for entry in entries]
    if not all_dates:
        return saved_paths

    folder = f"{min(all_dates)[0][:10]}_to_{max(all_dates)[1][:10]}"
    main_path = Path(save_base_path) / folder
    main_path.mkdir(parents=True, exist_ok=True)

    trajectory_names = list(trajectories.keys())
    for geometry, matches_iter in matching_trajectories.items():
        matches = list(matches_iter)
        geometry_path = main_path / geometry
        geometry_path.mkdir(parents=True, exist_ok=True)

        for chunk_start in range(0, len(matches), plots_per_file):
            chunk = matches[chunk_start : chunk_start + plots_per_file]
            rows = math.ceil(len(chunk) / 3)
            fig, axes = plt.subplots(rows, 3, subplot_kw={"projection": "polar"}, figsize=(15, 5 * rows))
            fig.suptitle(f"{_format_geometry_name(geometry)} alignment events", fontsize=14, fontweight="bold")
            if not isinstance(axes, IterableABC):
                axes = [axes]
            else:
                axes = list(getattr(axes, "flat", axes))

            for idx, (start, end, group) in enumerate(chunk):
                ax = axes[idx]
                ax.plot(0, 0, "o", label="Sun", color="#ffb000", markersize=7, markeredgecolor="black", markeredgewidth=0.4)
                plotted = set()
                for body in group:
                    coords = list(trajectories.get(body, []))
                    if body not in trajectory_names:
                        continue
                    color = colors[trajectory_names.index(body) % len(colors)]
                    event_points = [
                        coord_to_polar(coord)
                        for coord in coords
                        if _coord_time_iso(coord) and start <= _coord_time_iso(coord) <= end
                    ]
                    if not event_points:
                        continue

                    theta, radius = zip(*event_points)
                    label = _format_body_label(body)
                    if len(event_points) > 1:
                        ax.plot(theta, radius, color=color, linewidth=1.2, alpha=0.55)
                    ax.scatter(
                        theta,
                        radius,
                        color=color,
                        s=18,
                        marker="o",
                        edgecolors="white",
                        linewidths=0.5,
                        label=label if body not in plotted else "",
                        zorder=3,
                    )
                    plotted.add(body)

                ax.set_title(f"Event {chunk_start + idx + 1}: {start[:10]} to {end[:10]}", fontsize=10)
                ax.set_xlabel("Heliocentric longitude (rad)")
                ax.set_ylabel("Radius (km)", labelpad=18)
                ax.grid(alpha=0.25)
                ax.legend(loc="upper right", fontsize="small", frameon=True, framealpha=0.9)

            for empty_ax in axes[len(chunk) :]:
                empty_ax.set_visible(False)

            plt.tight_layout(h_pad=2, rect=(0, 0, 1, 0.95))
            base_filename = safe_filename(
                f"{geometry}_events_{chunk_start + 1:03d}-{chunk_start + len(chunk):03d}_"
                f"{chunk[0][0][:10]}_to_{chunk[-1][1][:10]}"
            )
            for file_format in formats:
                output_path = geometry_path / f"{base_filename}.{file_format}"
                plt.savefig(output_path, dpi=180, bbox_inches="tight")
                saved_paths.append(output_path)
            plt.close(fig)
    return saved_paths


def safe_filename(value: object) -> str:
    """Return a compact filesystem-safe filename stem."""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or "solarconflux_output"


def _coord_time_iso(coord: object) -> str:
    time_value = getattr(coord, "time", None)
    if time_value is not None:
        return str(time_value)
    obstime = getattr(coord, "obstime", None)
    if obstime is None:
        return ""
    if hasattr(obstime, "iso"):
        return str(obstime.iso)
    if hasattr(obstime, "datetime"):
        return obstime.datetime.strftime("%Y-%m-%d %H:%M:%S")
    return str(obstime)


def _format_body_label(body: str) -> str:
    return str(body).replace("_", " ").strip()


def _format_geometry_name(geometry: str) -> str:
    return str(geometry).replace("_", " ").replace("-", " ").title()


def _normalize_format(file_format: str) -> str:
    normalized = str(file_format).strip().lower().lstrip(".")
    if not normalized:
        raise ValueError("Plot format must not be empty.")
    return normalized
