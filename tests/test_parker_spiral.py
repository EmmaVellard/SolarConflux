import math
import unittest
from datetime import datetime

from solarconflux.angles import angular_separation_rad
from solarconflux.geometries import Geometry, TrajectoryPoint


ONE_AU_KM = 149_597_870.7


def geometry():
    trajectories = {
        "Earth": [
            TrajectoryPoint(
                time=datetime(2025, 1, 1),
                lon_rad=0.0,
                lat_rad=0.0,
                radius_km=ONE_AU_KM,
            )
        ]
    }
    return Geometry(trajectories.keys(), trajectories)


class ParkerSpiralTests(unittest.TestCase):
    def test_parker_spiral_output_is_finite(self):
        result = geometry().parker_spiral_function(ONE_AU_KM, math.radians(45), 400e3)

        self.assertTrue(math.isfinite(result))

    def test_parker_spiral_output_is_normalized(self):
        result = geometry().parker_spiral_function(ONE_AU_KM, math.radians(350), 400e3)

        self.assertGreaterEqual(result, 0.0)
        self.assertLess(result, 2.0 * math.pi)

    def test_radial_distance_increases_current_longitude_shift_magnitude(self):
        parker = geometry()

        near_shift = angular_separation_rad(
            0.0,
            parker.parker_spiral_function(50_000_000.0, 0.0, 400e3),
        )
        far_shift = angular_separation_rad(
            0.0,
            parker.parker_spiral_function(100_000_000.0, 0.0, 400e3),
        )

        self.assertGreater(far_shift, near_shift)

    def test_solar_wind_speed_decreases_current_longitude_shift_magnitude(self):
        parker = geometry()

        slow_shift = angular_separation_rad(
            0.0,
            parker.parker_spiral_function(ONE_AU_KM, 0.0, 400e3),
        )
        fast_shift = angular_separation_rad(
            0.0,
            parker.parker_spiral_function(ONE_AU_KM, 0.0, 800e3),
        )

        self.assertLess(fast_shift, slow_shift)

    def test_invalid_solar_wind_speed_raises_value_error(self):
        with self.assertRaises(ValueError):
            geometry().parker_spiral_function(ONE_AU_KM, 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
