import math
import unittest
from datetime import datetime

from solarconflux.angles import angular_separation_rad
from solarconflux.geometries import Geometry, TrajectoryPoint


ONE_AU_KM = 149_597_870.7
SOLAR_RADIUS_KM = 696_000.0
DEFAULT_SOLAR_ROTATION_PERIOD_DAYS = 25.38
DEFAULT_SOURCE_SURFACE_RADIUS_KM = 2.5 * SOLAR_RADIUS_KM


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


def expected_parker_source_longitude(
    r_km,
    lon_rad,
    u_sw_mps,
    solar_rotation_period_days=DEFAULT_SOLAR_ROTATION_PERIOD_DAYS,
    source_surface_radius_km=DEFAULT_SOURCE_SURFACE_RADIUS_KM,
):
    """Compute the documented Parker convention independently of production code."""
    omega_sun = 2.0 * math.pi / (solar_rotation_period_days * 24.0 * 3600.0)
    r_m = float(r_km) * 1e3
    r_source_m = float(source_surface_radius_km) * 1e3
    phi_source = float(lon_rad) + (omega_sun / float(u_sw_mps)) * (r_m - r_source_m)
    return phi_source % (2.0 * math.pi)


class ParkerSpiralTests(unittest.TestCase):
    def test_parker_spiral_output_is_finite(self):
        result = geometry().parker_spiral_function(ONE_AU_KM, math.radians(45), 400e3)

        self.assertTrue(math.isfinite(result))

    def test_parker_spiral_output_is_normalized(self):
        result = geometry().parker_spiral_function(ONE_AU_KM, math.radians(350), 400e3)

        self.assertGreaterEqual(result, 0.0)
        self.assertLess(result, 2.0 * math.pi)

    def test_parker_spiral_matches_independent_expected_calculation(self):
        parker = geometry()
        lon_rad = math.radians(25.0)
        speed = 450e3

        result = parker.parker_spiral_function(ONE_AU_KM, lon_rad, speed)
        expected = expected_parker_source_longitude(ONE_AU_KM, lon_rad, speed)

        self.assertAlmostEqual(result, expected)

    def test_reference_style_default_case_matches_documented_formula(self):
        parker = geometry()

        result = parker.parker_spiral_function(ONE_AU_KM, 0.0, 400e3)
        expected = expected_parker_source_longitude(ONE_AU_KM, 0.0, 400e3)

        self.assertAlmostEqual(result, expected)

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

    def test_different_solar_wind_speeds_produce_different_footpoints(self):
        parker = geometry()

        slow_footpoint = parker.parker_spiral_function(ONE_AU_KM, math.radians(15), 400e3)
        fast_footpoint = parker.parker_spiral_function(ONE_AU_KM, math.radians(15), 700e3)

        self.assertNotAlmostEqual(slow_footpoint, fast_footpoint)

    def test_invalid_solar_wind_speed_raises_value_error(self):
        with self.assertRaises(ValueError):
            geometry().parker_spiral_function(ONE_AU_KM, 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
