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
