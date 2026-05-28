import math
import unittest

from solarconflux.angles import angular_separation_rad, normalize_angle_rad, target_separation_rad


class AngleTests(unittest.TestCase):
    def test_normalize_angle_handles_negative_angles(self):
        self.assertAlmostEqual(normalize_angle_rad(math.radians(-10)), math.radians(350))

    def test_normalize_angle_handles_angles_greater_than_360(self):
        self.assertAlmostEqual(normalize_angle_rad(math.radians(370)), math.radians(10))

    def test_angular_separation_wraps_across_zero(self):
        separation = angular_separation_rad(math.radians(359), math.radians(1))
        self.assertAlmostEqual(separation, math.radians(2))

    def test_angular_separation_wraps_from_low_to_high_longitude(self):
        separation = angular_separation_rad(math.radians(10), math.radians(350))
        self.assertAlmostEqual(separation, math.radians(20))

    def test_angular_separation_handles_opposition(self):
        separation = angular_separation_rad(math.radians(0), math.radians(180))
        self.assertAlmostEqual(separation, math.radians(180))

    def test_target_separation_treats_270_as_90(self):
        self.assertAlmostEqual(target_separation_rad(math.radians(270)), math.radians(90))


if __name__ == "__main__":
    unittest.main()
