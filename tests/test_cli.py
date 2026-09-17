import argparse
import contextlib
import io
import math
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from solarconflux.cli import run_from_args
from solarconflux.geometries import TrajectoryPoint


class CliTests(unittest.TestCase):
    def test_cli_help_smoke(self):
        result = subprocess.run(
            [sys.executable, "-m", "solarconflux.cli", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--bodies", result.stdout)
        self.assertIn("--geometries", result.stdout)
        self.assertIn("--latitude-tolerance", result.stdout)
        self.assertIn("--list-bodies", result.stdout)
        self.assertIn("--plot-format", result.stdout)

    def test_cli_list_bodies_smoke(self):
        result = subprocess.run(
            [sys.executable, "-m", "solarconflux.cli", "--list-bodies"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Earth", result.stdout)
        self.assertIn("Solar Orbiter", result.stdout)

    def test_plot_format_requires_save_plots(self):
        result = subprocess.run(
            [sys.executable, "-m", "solarconflux.cli", "--plot-format", "pdf"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--plot-format requires --save-plots", result.stderr)


class ExcludedBodyTests(unittest.TestCase):
    """A body with no ephemeris in the window must leave the run, not end it.

    The backend already drops such a body and explains why, but the CLI used to keep it in
    the screened list, so the run died on an internal "Missing trajectories" error instead of
    screening the bodies that were actually covered.
    """

    NOTE = "excluded: outside its ephemeris coverage, which starts 2018-08-12 08:16 TDB"

    def args(self, output_dir):
        return argparse.Namespace(
            bodies="Earth,Venus,PSP", start_time="2017-01-01", end_time="2017-01-05",
            step="1d", source="horizons", geometries="cone", cone_width=10.0, tolerance=10.0,
            latitude_tolerance=None, arbitrary_angle=None, solar_wind_speed=400.0,
            output_dir=output_dir, save_plots=False, plot_format=None, verbose=False,
            export_trajectories=False,
        )

    def run_cli(self):
        def retrieve(bodies, *args, **kwargs):
            covered = {
                name: [TrajectoryPoint(datetime(2017, 1, 1) + timedelta(days=i),
                                       math.radians(i), 0.0, 1.5e8) for i in range(5)]
                for name in bodies if name != "PSP"
            }
            return covered, {name: "horizons" for name in covered}, {"PSP": self.NOTE}

        with tempfile.TemporaryDirectory() as tmpdir:
            output = io.StringIO()
            with patch("solarconflux.cli.retrieve_trajectories", side_effect=retrieve):
                with contextlib.redirect_stdout(output):
                    run_from_args(self.args(tmpdir))
            return output.getvalue(), sorted(p.name for p in Path(tmpdir).rglob("*.csv"))

    def test_run_completes_and_screens_the_covered_bodies(self):
        _, csvs = self.run_cli()
        self.assertEqual(len(csvs), 1)

    def test_the_exclusion_is_reported_without_requiring_verbose(self):
        printed, _ = self.run_cli()
        self.assertIn("PSP", printed)
        self.assertIn(self.NOTE, printed)


if __name__ == "__main__":
    unittest.main()
