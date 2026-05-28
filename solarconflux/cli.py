"""Command-line interface for SolarConflux."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional

from . import __version__
from .bodies import get_infos, horizons_ids_for_bodies, validate_body_names
from .export import save_match, save_run_metadata
from .functions import build_run_parameters, matching_dates
from .plotting import save_plot
from .trajectories import get_info, get_trajectories
from .validation import (
    normalize_geometry_choices,
    validate_date_range,
    validate_optional_latitude_tolerance_degrees,
    validate_step,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solarconflux",
        description="Retrieve heliocentric trajectories and detect approximate geometric alignments.",
        epilog=(
            "Example: solarconflux --bodies Earth,Venus --start-time 2025-01-01 "
            "--end-time 2025-02-01 --geometries opposition,quadrature --output-dir results"
        ),
    )
    parser.add_argument("--interactive", action="store_true", help="Run beginner-friendly interactive prompts.")
    parser.add_argument(
        "--list-bodies",
        action="store_true",
        help="Print supported bodies, Horizons IDs, and available date ranges, then exit.",
    )
    parser.add_argument("--bodies", help="Comma-separated bodies, for example Earth,Venus,Solar Orbiter.")
    parser.add_argument("--start-time", help="Start time, for example 2025-01-01 or 2025-01-01 12:00.")
    parser.add_argument("--end-time", help="End time, for example 2025-12-31.")
    parser.add_argument("--step", default="60m", help="Horizons time step, for example 60m, 1h, or 1d.")
    parser.add_argument(
        "--geometries",
        help="Comma-separated modes: opposition, quadrature, cone, arbitrary, parker, coneparker.",
    )
    parser.add_argument("--cone-width", type=float, default=10.0, help="Cone width in degrees.")
    parser.add_argument("--tolerance", type=float, default=10.0, help="Angular tolerance in degrees.")
    parser.add_argument(
        "--latitude-tolerance",
        type=float,
        help="Optional heliographic latitude span tolerance in degrees.",
    )
    parser.add_argument("--arbitrary-angle", type=float, help="Arbitrary angle in degrees.")
    parser.add_argument(
        "--solar-wind-speed",
        type=float,
        default=400.0,
        help="Solar wind speed for Parker spiral modes in km/s.",
    )
    parser.add_argument("--output-dir", default="solarconflux_output", help="Directory for CSV, metadata, and plots.")
    plot_group = parser.add_mutually_exclusive_group()
    plot_group.add_argument("--save-plots", dest="save_plots", action="store_true", help="Save polar plots.")
    plot_group.add_argument("--no-plots", dest="save_plots", action="store_false", help="Do not save plots.")
    parser.set_defaults(save_plots=False)
    parser.add_argument(
        "--plot-format",
        help="Comma-separated plot formats used with --save-plots, for example png,pdf. Default: png.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print progress messages.")
    parser.add_argument("--version", action="version", version=f"solarconflux {__version__}")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list_bodies:
            print_supported_bodies()
            return 0

        if args.plot_format and not args.save_plots:
            parser.error("--plot-format requires --save-plots.")

        if args.interactive or not _has_noninteractive_args(args):
            return run_interactive()

        missing = [
            option
            for option, value in {
                "--bodies": args.bodies,
                "--start-time": args.start_time,
                "--end-time": args.end_time,
                "--geometries": args.geometries,
            }.items()
            if not value
        ]
        if missing:
            parser.error("Missing required non-interactive option(s): " + ", ".join(missing))

        run_from_args(args)
    except (ImportError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")
    return 0


def run_from_args(args: argparse.Namespace) -> None:
    bodies = validate_body_names(args.bodies)
    geometries = normalize_geometry_choices(args.geometries)
    validate_date_range(args.start_time, args.end_time)
    step = validate_step(args.step)
    latitude_tolerance_deg = validate_optional_latitude_tolerance_degrees(args.latitude_tolerance)
    plot_formats = _parse_plot_formats(args.plot_format)

    if "arbitrary" in geometries and args.arbitrary_angle is None:
        raise ValueError("--arbitrary-angle is required when using the arbitrary geometry.")
    if args.plot_format and not args.save_plots:
        raise ValueError("--plot-format requires --save-plots.")

    output_dir = Path(args.output_dir)
    parameters = build_run_parameters(
        cone_width_degrees=args.cone_width,
        tolerance_degrees=args.tolerance,
        arbitrary_angle_degrees=args.arbitrary_angle,
        latitude_tolerance_deg=latitude_tolerance_deg,
        solar_wind_speed_km_s=args.solar_wind_speed,
    )

    if args.verbose:
        print("Fetching trajectories...")
    trajectories = get_trajectories(bodies, args.start_time, args.end_time, step)

    if args.verbose:
        print("Looking for matching dates...")
    matches = matching_dates(
        geometries,
        bodies,
        trajectories,
        cone_width=args.cone_width,
        tolerance=args.tolerance,
        arbitrary_angle=args.arbitrary_angle,
        latitude_tolerance_deg=latitude_tolerance_deg,
        u_sw=args.solar_wind_speed * 1000.0,
        angle_unit="deg",
        verbose=args.verbose,
    )

    csv_path = save_match(matches, output_dir, parameters=parameters)
    output_files = [csv_path]

    if args.save_plots:
        output_files.extend(save_plot(matches, trajectories, output_dir, formats=plot_formats))

    save_run_metadata(
        csv_path.parent,
        parameters={**parameters, "step": step, "geometries": geometries},
        body_list=bodies,
        horizons_ids=horizons_ids_for_bodies(bodies),
        package_version=__version__,
        output_files=output_files,
    )

    if args.verbose:
        print(f"Saved results to {csv_path.parent}")


def run_interactive() -> int:
    print("\nAvailable bodies for trajectory retrieval:")
    get_info()

    bodies = input(
        "\nEnter bodies (comma-separated, e.g., BepiColombo,Solar Orbiter,Earth): "
    ).strip()
    start_time = input("\nEnter the start time (e.g., 2025-01-01): ").strip()
    end_time = input("Enter the end time (e.g., 2025-12-31): ").strip()

    step_choice = input("\nChoose the time step? y/n (default: 60m): ").strip().lower()
    step = input("Enter the time step (e.g., 60m): ").strip() if step_choice == "y" else "60m"

    print("\nAvailable geometric alignments: opposition, cone, quadrature, arbitrary, parker, coneparker")
    geometries = input("Enter alignment types (comma-separated): ").strip()

    normalized_geometries = normalize_geometry_choices(geometries)
    latitude_choice = input("\nApply an optional latitude filter? y/n (default: no): ").strip().lower()
    latitude_tolerance = None
    if latitude_choice == "y":
        latitude_tolerance = float(input("Enter latitude tolerance in degrees: ").strip())

    arbitrary_angle = None
    if "arbitrary" in normalized_geometries:
        arbitrary_angle = float(input("Enter the desired angle in degrees: ").strip())

    solar_wind_speed = 400.0
    if "parker" in normalized_geometries or "coneparker" in normalized_geometries:
        speed_choice = input("\nChoose the solar wind speed? y/n (default: 400 km/s): ").strip().lower()
        if speed_choice == "y":
            solar_wind_speed = float(input("Enter solar wind speed for Parker spiral (km/s): ").strip())

    output_dir = input("\nEnter the output folder path: ").strip() or "solarconflux_output"
    plot_choice = input("\nSave plots? y/n (CSV is always saved): ").strip().lower()

    args = argparse.Namespace(
        bodies=bodies,
        start_time=start_time,
        end_time=end_time,
        step=step,
        geometries=geometries,
        cone_width=10.0,
        tolerance=10.0,
        latitude_tolerance=latitude_tolerance,
        arbitrary_angle=arbitrary_angle,
        solar_wind_speed=solar_wind_speed,
        output_dir=output_dir,
        save_plots=plot_choice == "y",
        plot_format="png",
        verbose=True,
    )
    run_from_args(args)
    return 0


def _has_noninteractive_args(args: argparse.Namespace) -> bool:
    return any([args.bodies, args.start_time, args.end_time, args.geometries])


def print_supported_bodies() -> None:
    """Print supported body metadata for CLI users."""
    print("Supported bodies:\n")
    print(f"{'Body':<16} {'Horizons ID':<22} {'Available date range'}")
    print(f"{'-' * 16} {'-' * 22} {'-' * 20}")
    for body, info in get_infos().items():
        horizons_id = str(info["id"])
        date_range = f"{info['start']} to {info['end']}"
        print(f"{body:<16} {horizons_id:<22} {date_range}")


def _parse_plot_formats(value: Optional[str]) -> List[str]:
    """Return normalized plot format strings from a comma-separated CLI value."""
    if value is None:
        return ["png"]
    formats = [item.strip().lower().lstrip(".") for item in value.split(",")]
    formats = [item for item in formats if item]
    if not formats:
        raise ValueError("--plot-format must include at least one format.")
    return formats


if __name__ == "__main__":
    raise SystemExit(main())
