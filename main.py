"""Compatibility wrapper for running SolarConflux from the repository root."""

from __future__ import annotations

from solarconflux.cli import main


def SolarConflux() -> int:
    """Run the interactive SolarConflux workflow."""
    return main(["--interactive"])


if __name__ == "__main__":
    raise SystemExit(main())
