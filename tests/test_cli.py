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


if __name__ == "__main__":
    unittest.main()
