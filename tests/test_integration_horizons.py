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
    "Set SOLARCONFLUX_RUN_INTEGRATION=1 to run live Horizons tests.",
)
class HorizonsIntegrationTests(unittest.TestCase):
    def test_fetches_earth_trajectory(self):
        trajectories = get_trajectories(["Earth"], "2025-01-01", "2025-01-02", "1d")

        self.assertIn("Earth", trajectories)


if __name__ == "__main__":
    unittest.main()
