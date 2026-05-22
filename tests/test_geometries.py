import math
import unittest
from datetime import datetime, timedelta

from solarconflux.functions import matching_dates
from solarconflux.geometries import Geometry, TrajectoryPoint


def point(hour, lon_deg, lat_deg=0.0, radius_km=149_597_870.7):
    return TrajectoryPoint(
        time=datetime(2025, 1, 1) + timedelta(hours=hour),
        lon_rad=math.radians(lon_deg),
        lat_rad=math.radians(lat_deg),
        radius_km=radius_km,
    )


class CoordinateWithoutLatitude:
    def __init__(self, hour, lon_deg):
        self.time = datetime(2025, 1, 1) + timedelta(hours=hour)
        self.spherical = type(
            "SphericalWithoutLatitude",
            (),
            {"lon": math.radians(lon_deg), "distance": 149_597_870.7},
        )()


class GeometryTests(unittest.TestCase):
    def test_opposition_wraps_near_zero_degrees(self):
        trajectories = {"Earth": [point(0, 359)], "Venus": [point(0, 179)]}
        geometry = Geometry(trajectories.keys(), trajectories)

        matches = geometry.check_geometry("opposition")

        self.assertEqual(matches, [("2025-01-01 00:00:00", "2025-01-01 00:00:00", ["Earth", "Venus"])])

    def test_cone_wraps_near_zero_degrees(self):
        trajectories = {"Earth": [point(0, 358)], "Venus": [point(0, 2)]}
        geometry = Geometry(trajectories.keys(), trajectories, cone_width=math.radians(5))

        matches = geometry.check_geometry("cone")

        self.assertEqual(len(matches), 1)

    def test_longitude_match_passes_without_latitude_filter(self):
        trajectories = {"Earth": [point(0, 358, -20)], "Venus": [point(0, 2, 20)]}
        geometry = Geometry(trajectories.keys(), trajectories, cone_width=math.radians(5))

        matches = geometry.check_geometry("cone")

        self.assertEqual(len(matches), 1)

    def test_latitude_filter_rejects_match_above_span(self):
        trajectories = {"Earth": [point(0, 358, -20)], "Venus": [point(0, 2, 20)]}
        geometry = Geometry(
            trajectories.keys(),
            trajectories,
            cone_width=math.radians(5),
            latitude_tolerance=math.radians(30),
        )

        matches = geometry.check_geometry("cone")

        self.assertEqual(matches, [])

    def test_latitude_filter_allows_match_within_span(self):
        trajectories = {"Earth": [point(0, 358, -2)], "Venus": [point(0, 2, 2)]}
        geometry = Geometry(
            trajectories.keys(),
            trajectories,
            cone_width=math.radians(5),
            latitude_tolerance=math.radians(5),
        )

        matches = geometry.check_geometry("cone")

        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].latitude_span_deg, 4)

    def test_public_api_latitude_filter_uses_degrees(self):
        trajectories = {"Earth": [point(0, 358, -2)], "Venus": [point(0, 2, 2)]}

        matches = matching_dates(
            ["cone"],
            ["Earth", "Venus"],
            trajectories,
            cone_width=5,
            latitude_tolerance_deg=3,
            verbose=False,
        )

        self.assertNotIn("cone", matches)

    def test_latitude_filter_uses_group_span_for_three_bodies(self):
        trajectories = {
            "Earth": [point(0, 0, -3)],
            "Venus": [point(0, 2, 0)],
            "Mars": [point(0, 4, 3)],
        }
        geometry = Geometry(
            trajectories.keys(),
            trajectories,
            cone_width=math.radians(5),
            latitude_tolerance=math.radians(6),
        )

        matches = geometry.check_geometry("cone")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].group, ["Earth", "Mars", "Venus"])
        self.assertAlmostEqual(matches[0].latitude_span_deg, 6)

    def test_latitude_filter_rejects_three_body_group_above_span(self):
        trajectories = {
            "Earth": [point(0, 0, -4)],
            "Venus": [point(0, 2, 0)],
            "Mars": [point(0, 4, 4)],
        }
        geometry = Geometry(
            trajectories.keys(),
            trajectories,
            cone_width=math.radians(5),
            latitude_tolerance=math.radians(6),
        )

        matches = geometry.check_geometry("cone")

        self.assertEqual(matches, [])

    def test_latitude_filter_requires_latitude_data(self):
        trajectories = {
            "Earth": [CoordinateWithoutLatitude(0, 358)],
            "Venus": [CoordinateWithoutLatitude(0, 2)],
        }
        geometry = Geometry(
            trajectories.keys(),
            trajectories,
            cone_width=math.radians(5),
            latitude_tolerance=math.radians(5),
        )

        with self.assertRaisesRegex(ValueError, "Latitude data"):
            geometry.check_geometry("cone")

    def test_quadrature_uses_longitude_not_latitude_only(self):
        trajectories = {"Earth": [point(0, 10, 0)], "Venus": [point(0, 10, 90)]}
        geometry = Geometry(trajectories.keys(), trajectories)

        self.assertEqual(geometry.check_geometry("quadrature"), [])

    def test_quadrature_wraps_270_degree_configuration(self):
        trajectories = {"Earth": [point(0, 350)], "Venus": [point(0, 80)]}
        geometry = Geometry(trajectories.keys(), trajectories)

        self.assertEqual(len(geometry.check_geometry("quadrature")), 1)

    def test_arbitrary_angle_public_api_accepts_degrees(self):
        trajectories = {"Earth": [point(0, 350)], "Venus": [point(0, 20)]}

        matches = matching_dates(
            ["arbitrary"],
            ["Earth", "Venus"],
            trajectories,
            arbitrary_angle=30,
            tolerance=1,
            angle_unit="deg",
            verbose=False,
        )

        self.assertIn("arbitrary", matches)

    def test_direct_arbitrary_rejects_negative_radian_angle(self):
        trajectories = {"Earth": [point(0, 350)], "Venus": [point(0, 20)]}
        geometry = Geometry(trajectories.keys(), trajectories)

        with self.assertRaises(ValueError):
            geometry.check_geometry("arbitrary", arbitrary_angle=-math.radians(30))

    def test_parker_footpoint_comparison_wraps(self):
        trajectories = {"Earth": [point(0, 359)], "Venus": [point(0, 1)]}
        geometry = Geometry(trajectories.keys(), trajectories)

        matches = geometry.check_geometry("parker", u_sw=400e3)

        self.assertEqual(len(matches), 1)

    def test_coneparker_requires_cone_and_parker_conditions(self):
        trajectories = {"Earth": [point(0, 359)], "Venus": [point(0, 1)]}
        geometry = Geometry(trajectories.keys(), trajectories, cone_width=math.radians(5))

        matches = geometry.check_geometry("coneparker", u_sw=400e3)

        self.assertEqual(len(matches), 1)


if __name__ == "__main__":
    unittest.main()
