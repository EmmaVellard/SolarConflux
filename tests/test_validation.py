import unittest

from solarconflux.bodies import validate_body_names
from solarconflux.functions import matching_dates
from solarconflux.geometries import Geometry
from solarconflux.validation import (
    angle_to_radians,
    normalize_geometry_choices,
    validate_date_range,
    validate_solar_wind_speed_mps,
    validate_step,
)


class ValidationTests(unittest.TestCase):
    def test_empty_body_list_is_invalid(self):
        with self.assertRaises(ValueError):
            validate_body_names([])

    def test_unknown_body_is_invalid(self):
        with self.assertRaises(ValueError):
            validate_body_names(["NotARealProbe"])

    def test_invalid_date_range_is_invalid(self):
        with self.assertRaises(ValueError):
            validate_date_range("2025-02-01", "2025-01-01")

    def test_invalid_step_is_invalid(self):
        with self.assertRaises(ValueError):
            validate_step("0m")

    def test_unsupported_geometry_is_invalid(self):
        with self.assertRaises(ValueError):
            normalize_geometry_choices(["syzygy-ish"])

    def test_invalid_angle_unit_is_invalid(self):
        with self.assertRaises(ValueError):
            angle_to_radians(10, "turns", "angle")

    def test_negative_arbitrary_angle_is_invalid(self):
        with self.assertRaises(ValueError):
            matching_dates(
                ["arbitrary"],
                ["Earth"],
                {"Earth": [object()]},
                arbitrary_angle=-1,
                verbose=False,
            )

    def test_invalid_solar_wind_speed_is_invalid(self):
        with self.assertRaises(ValueError):
            validate_solar_wind_speed_mps(-1)

    def test_geometry_rejects_empty_trajectories(self):
        with self.assertRaises(ValueError):
            Geometry([], {})

    def test_matching_dates_rejects_arbitrary_without_angle(self):
        with self.assertRaises(ValueError):
            matching_dates(["arbitrary"], ["Earth"], {"Earth": [object()]}, verbose=False)


if __name__ == "__main__":
    unittest.main()
