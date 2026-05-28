import subprocess
import sys
import unittest


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


if __name__ == "__main__":
    unittest.main()
