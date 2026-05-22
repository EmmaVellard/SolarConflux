import unittest

from solarconflux.plotting import safe_filename


class PlottingTests(unittest.TestCase):
    def test_safe_filename_removes_unsafe_characters(self):
        filename = safe_filename("Cone Parker: 2025-01-01 to 2025/01/02")

        self.assertEqual(filename, "cone_parker_2025-01-01_to_2025_01_02")

    def test_safe_filename_has_fallback(self):
        self.assertEqual(safe_filename("   !!!   "), "solarconflux_output")


if __name__ == "__main__":
    unittest.main()
