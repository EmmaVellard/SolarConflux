import csv
import json
import tempfile
import unittest
from pathlib import Path

from solarconflux.events import MatchEntry
from solarconflux.export import CSV_COLUMNS, save_match, save_run_metadata


class ExportTests(unittest.TestCase):
    def test_save_match_writes_scientific_columns(self):
        matches = {
            "cone": [
                MatchEntry(
                    "2025-01-01 00:00:00",
                    "2025-01-01 02:00:00",
                    ["Earth", "Venus"],
                    latitude_span_deg=4.0,
                ),
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = save_match(
                matches,
                tmpdir,
                parameters={
                    "tolerance_degrees": 5,
                    "cone_width_degrees": 10,
                    "latitude_tolerance_deg": 5,
                    "solar_wind_speed_km_s": 400,
                },
            )

            with csv_path.open() as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows[0].keys()), CSV_COLUMNS)
        self.assertEqual(rows[0]["event_id"], "1")
        self.assertEqual(rows[0]["geometry"], "cone")
        self.assertEqual(rows[0]["bodies"], "Earth;Venus")
        self.assertEqual(rows[0]["number_of_bodies"], "2")
        self.assertEqual(rows[0]["duration_hours"], "2")
        self.assertEqual(rows[0]["duration_days"], "0.0833333")
        self.assertEqual(rows[0]["latitude_tolerance_deg"], "5")
        self.assertEqual(rows[0]["latitude_span_deg"], "4")
        self.assertEqual(rows[0]["cone_width_deg"], "10")

    def test_save_match_writes_headers_when_no_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = save_match({}, tmpdir)

            with csv_path.open() as handle:
                reader = csv.reader(handle)
                rows = list(reader)

        self.assertEqual(rows, [CSV_COLUMNS])
        self.assertEqual(csv_path.name, "solarconflux_results.csv")

    def test_save_run_metadata_writes_assumptions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = save_run_metadata(
                Path(tmpdir),
                {"step": "60m", "latitude_tolerance_deg": 5},
                ["Earth"],
                {"Earth": 399},
                output_files=["results.csv", "plot.png"],
            )

            metadata = json.loads(metadata_path.read_text())

        self.assertIn("SolarConflux is not a full heliospheric MHD model.", metadata["assumptions"])
        self.assertEqual(metadata["horizons_ids"]["Earth"], 399)
        self.assertEqual(metadata["input_parameters"]["latitude_tolerance_deg"], 5)
        self.assertEqual(metadata["generated_output_filenames"], ["plot.png", "results.csv"])


if __name__ == "__main__":
    unittest.main()
