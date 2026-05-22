import csv
import tempfile
import unittest
from pathlib import Path

from solarconflux.export import save_match, save_run_metadata


class ExportTests(unittest.TestCase):
    def test_save_match_writes_scientific_columns(self):
        matches = {
            "cone": [
                ("2025-01-01 00:00:00", "2025-01-01 02:00:00", ["Earth", "Venus"]),
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = save_match(
                matches,
                tmpdir,
                parameters={
                    "tolerance_degrees": 5,
                    "cone_width_degrees": 10,
                    "solar_wind_speed_km_s": 400,
                },
            )

            with csv_path.open() as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["geometry"], "cone")
        self.assertEqual(rows[0]["bodies"], "Earth;Venus")
        self.assertEqual(rows[0]["number_of_bodies"], "2")
        self.assertEqual(rows[0]["duration_hours"], "2")
        self.assertEqual(rows[0]["cone_width_deg"], "10")

    def test_save_run_metadata_writes_assumptions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = save_run_metadata(Path(tmpdir), {"step": "60m"}, ["Earth"], {"Earth": 399})

            text = metadata_path.read_text()

        self.assertIn("SolarConflux is not a full heliospheric MHD model", text)
        self.assertIn("\"Earth\": 399", text)


if __name__ == "__main__":
    unittest.main()
