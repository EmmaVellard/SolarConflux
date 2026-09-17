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


class EventOrderingTests(unittest.TestCase):
    """event_id must follow the science, not the order the modes happened to be requested."""

    ENTRIES = {
        "cone": [MatchEntry("2025-01-01 00:00:00", "2025-02-03 00:00:00", ["Earth", "Mars"])],
        "arbitrary": [MatchEntry("2025-01-01 00:00:00", "2025-01-24 00:00:00", ["Earth", "Venus"])],
    }

    def rows(self, entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = save_match(entries, tmpdir)
            with csv_path.open() as handle:
                return [(row["event_id"], row["geometry"], row["bodies"]) for row in csv.DictReader(handle)]

    def test_requesting_the_same_modes_in_either_order_numbers_events_identically(self):
        reversed_order = {key: self.ENTRIES[key] for key in reversed(list(self.ENTRIES))}
        self.assertEqual(self.rows(dict(self.ENTRIES)), self.rows(reversed_order))

    def test_events_sharing_a_start_time_are_ordered_by_geometry_then_bodies(self):
        self.assertEqual(
            self.rows(self.ENTRIES),
            [("1", "arbitrary", "Earth;Venus"), ("2", "cone", "Earth;Mars")],
        )


if __name__ == "__main__":
    unittest.main()
