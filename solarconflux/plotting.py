"""Plotting helpers for SolarConflux outputs."""

from __future__ import annotations

import math
from collections.abc import Iterable as IterableABC
from pathlib import Path
from typing import Iterable, Mapping, Tuple

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
) -> None:
    """Save polar plots of matched spacecraft positions."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError("Plotting requires matplotlib.") from exc

    colors = ["blue", "red", "purple", "cyan", "green", "brown", "limegreen", "gold", "grey", "pink"]
    plots_per_file = 15

    all_dates = [(entry[0], entry[1]) for entries in matching_trajectories.values() for entry in entries]
    if not all_dates:
        return

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
            if not isinstance(axes, IterableABC):
                axes = [axes]
            else:
                axes = list(getattr(axes, "flat", axes))

            for idx, (start, end, group) in enumerate(chunk):
                ax = axes[idx]
                ax.plot(0, 0, "o", label="Sun", color="orange", markersize=5)
                plotted = set()
                for body in group:
                    coords = trajectories.get(body, [])
                    if body not in trajectory_names:
                        continue
                    color = colors[trajectory_names.index(body) % len(colors)]
                    for coord in coords:
                        coord_time = _coord_time_iso(coord)
                        if coord_time and start <= coord_time <= end:
                            ax.scatter(*coord_to_polar(coord), color=color, s=5, label=body if body not in plotted else "")
                            plotted.add(body)
                ax.set_title(f"{geometry}: {start[:10]} to {end[:10]}")
                ax.set_xlabel("Heliocentric longitude")
                ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=2)

            for empty_ax in axes[len(chunk) :]:
                empty_ax.set_visible(False)

            plt.tight_layout(h_pad=2)
            plt.savefig(geometry_path / f"{chunk[0][0][:10]}_to_{chunk[-1][1][:10]}.png")
            plt.close(fig)


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
