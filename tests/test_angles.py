import math
import unittest

from solarconflux.angles import angular_separation_rad, normalize_angle_rad, target_separation_rad


class AngleTests(unittest.TestCase):
    def test_normalize_angle(self):
        self.assertAlmostEqual(normalize_angle_rad(math.radians(370)), math.radians(10))

    def test_angular_separation_wraps_across_zero(self):
        separation = angular_separation_rad(math.radians(359), math.radians(1))
        self.assertAlmostEqual(separation, math.radians(2))

    def test_target_separation_treats_270_as_90(self):
        self.assertAlmostEqual(target_separation_rad(math.radians(270)), math.radians(90))


if __name__ == "__main__":
    unittest.main()
