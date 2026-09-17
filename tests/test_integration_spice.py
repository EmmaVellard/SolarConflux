import os
import unittest

from solarconflux.trajectories import get_trajectories

try:
    import pytest

    pytestmark = pytest.mark.integration
except ImportError:
    pytestmark = []


@unittest.skipUnless(
    os.environ.get("SOLARCONFLUX_RUN_INTEGRATION") == "1",
    "Set SOLARCONFLUX_RUN_INTEGRATION=1 to run live SPICE tests (downloads kernels).",
)
class SpiceIntegrationTests(unittest.TestCase):
    """Confirm the SPICE and Horizons backends agree.

    Both ultimately reach the Heliocentric Inertial frame through the same SunPy
    transform, so a body whose ephemeris comes from the same underlying source must agree
    to numerical precision. A systematic longitude offset here means the frame conversion
    has drifted -- an earlier hand-rolled HCI frame kernel failed exactly that way.
    """

    START = "2025-01-01"
    END = "2025-01-03"
    STEP = "1d"

    def residuals(self, body, start=None, end=None):
        import astropy.units as u

        spice = get_trajectories([body], start or self.START, end or self.END, self.STEP, source="spice")[body]
        horizons = get_trajectories([body], start or self.START, end or self.END, self.STEP, source="horizons")[body]
        self.assertEqual(len(spice), len(horizons))
        return (
            max(abs((spice.lon - horizons.lon).to_value(u.arcsec))),
            max(abs((spice.lat - horizons.lat).to_value(u.arcsec))),
            max((spice.cartesian - horizons.cartesian).norm().to_value(u.km)),
        )

    def test_planets_agree_to_numerical_precision(self):
        for body in ("Earth", "Venus", "Mars"):
            with self.subTest(body=body):
                dlon, dlat, sep = self.residuals(body)
                self.assertLess(dlon, 1e-3, "longitude offset suggests a frame conversion error")
                self.assertLess(dlat, 1e-3)
                self.assertLess(sep, 1.0)

    def test_jupiter_matches_within_the_barycentre_offset(self):
        # de440s.bsp has no Jupiter centre, so SPICE reads the system barycentre.
        _, _, sep = self.residuals("Jupiter")
        self.assertLess(sep, 300.0)

    def test_spacecraft_sharing_an_archive_with_horizons_agree(self):
        for body in ("BepiColombo", "Juice"):
            with self.subTest(body=body):
                _, _, sep = self.residuals(body)
                self.assertLess(sep, 50.0)

    def test_europa_clipper_uses_flown_not_reference_trajectory(self):
        # The long ref_trj is a design trajectory and is ~1900 km from the flown one, so
        # this fails if the operational arcs stop being selected or ordered by data cutoff.
        _, _, sep = self.residuals("Europa Clipper", "2025-04-01", "2025-04-03")
        self.assertLess(sep, 50.0)

    def test_juno_uses_reconstructed_not_predicted_cruise(self):
        # The cruise merge file is predicted after 2013 and is ~3000 km out on its own.
        _, _, sep = self.residuals("Juno", "2016-06-01", "2016-06-03")
        self.assertLess(sep, 50.0)

    def test_requesting_a_spacecraft_does_not_perturb_planet_positions(self):
        # Mission SPKs bundle planetary segments, so a wrong furnish order would make
        # Earth's position depend on which spacecraft was requested alongside it.
        import astropy.units as u

        alone = get_trajectories(["Earth"], self.START, self.END, self.STEP, source="spice")["Earth"]
        with_craft = get_trajectories(
            ["Earth", "Europa Clipper"], self.START, self.END, self.STEP, source="spice"
        )["Earth"]
        offset = max((alone.cartesian - with_craft.cartesian).norm().to_value(u.km))
        self.assertLess(offset, 1e-6)

    def test_unsupported_bodies_fail_clearly(self):
        for body in ("ACE", "SDO"):
            with self.subTest(body=body), self.assertRaises(ValueError) as caught:
                get_trajectories([body], self.START, self.END, self.STEP, source="spice")
            self.assertIn(body, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
