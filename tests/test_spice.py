import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from solarconflux import spice
from solarconflux.browser import trajectory_bundle
from solarconflux.geometries import TrajectoryPoint
from solarconflux.validation import step_to_seconds, validate_source


class SourceValidationTests(unittest.TestCase):
    def test_accepts_known_sources_and_defaults_to_horizons(self):
        self.assertEqual(validate_source("spice"), "spice")
        self.assertEqual(validate_source(" HORIZONS "), "horizons")
        self.assertEqual(validate_source(None), "horizons")

    def test_rejects_unknown_source(self):
        with self.assertRaisesRegex(ValueError, "Unsupported trajectory source"):
            validate_source("cspice")


class StepToSecondsTests(unittest.TestCase):
    def test_converts_each_supported_unit(self):
        for step, expected in (("30s", 30), ("60m", 3600), ("6h", 21600), ("1d", 86400), ("0.5h", 1800)):
            with self.subTest(step=step):
                self.assertEqual(step_to_seconds(step), expected)

    def test_rejects_invalid_step(self):
        with self.assertRaises(ValueError):
            step_to_seconds("0h")


class UnsupportedBodyTests(unittest.TestCase):
    def test_ace_and_sdo_are_rejected_by_name(self):
        for body in ("ACE", "SDO"):
            with self.subTest(body=body), self.assertRaises(ValueError) as caught:
                spice.get_spice_trajectories([body, "Earth"], "2020-01-01", "2020-01-02", "1d")
            self.assertIn(body, str(caught.exception))
            self.assertIn("horizons", str(caught.exception))

    def test_unsupported_bodies_are_absent_from_the_manifest(self):
        for body in spice.UNSUPPORTED_BODIES:
            self.assertNotIn(body, spice._MANIFEST)
            self.assertNotIn(body, spice.spice_supported_bodies())


class TargetMappingTests(unittest.TestCase):
    def test_mars_and_jupiter_use_system_barycentres(self):
        # de440s.bsp carries no body centre for either planet.
        self.assertEqual(spice._TARGETS["Mars"], ("MARS BARYCENTER", 4))
        self.assertEqual(spice._TARGETS["Jupiter"], ("JUPITER BARYCENTER", 5))

    def test_every_supported_body_has_a_target(self):
        for body in spice.spice_supported_bodies():
            self.assertIn(body, spice._TARGETS)


class KernelDirTests(unittest.TestCase):
    def test_environment_variable_overrides_default(self):
        with patch.dict("os.environ", {"SOLARCONFLUX_KERNEL_DIR": "/tmp/kernels-xyz"}):
            self.assertEqual(str(spice.kernel_dir()), "/tmp/kernels-xyz")

    def test_default_is_under_the_home_directory(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertTrue(str(spice.kernel_dir()).endswith(".solarconflux/kernels"))


class WindowFilterTests(unittest.TestCase):
    def test_maven_and_soho_and_trj_windows_are_parsed(self):
        self.assertEqual(
            spice._window_from_name("maven", "maven_orb_rec_150101_150401_v1.bsp"),
            (datetime(2015, 1, 1), datetime(2015, 4, 1)),
        )
        self.assertEqual(
            spice._window_from_name("soho", "soho_1998a.bsp"),
            (datetime(1998, 1, 1), datetime(1999, 1, 1)),
        )
        self.assertEqual(
            spice._window_from_name("trj", "trj_250515-250626-dco2507090443-cruise006-reconstruct-OD067-v1.bsp"),
            (datetime(2025, 5, 15), datetime(2025, 6, 26)),
        )

    def test_only_overlapping_kernels_are_selected(self):
        window = (datetime(2015, 1, 1), datetime(2015, 4, 1))
        self.assertTrue(spice._overlaps(window, datetime(2015, 2, 1), datetime(2015, 2, 2)))
        self.assertFalse(spice._overlaps(window, datetime(2016, 1, 1), datetime(2016, 1, 2)))
        # A spec with no declared window always applies.
        self.assertTrue(spice._overlaps(None, datetime(1990, 1, 1), datetime(1990, 1, 2)))


class EuropaClipperSelectionTests(unittest.TestCase):
    LISTING = " ".join([
        "ref_trj_241014_340903_21F31_MEGA_L241014_A300411_LP05_V7_scpse.bsp",
        "trj_250104-250614-dco2502250958-cruise005-final-OD042-v1.bsp",
        "trj_250215-250614-dco2503050213-MGACU1-PRELIM-OD045-v1.bsp",
        "trj_250215-250614-dco2503101633-MGACU1-FINAL-OD046-v1-noburn.bsp",
        "trj_250318-250905-dco2505280203-cruise007-final-OD061-v1.bsp",
        "trj_260401-260919-dco2605201244-cruise016-predict-OD084-v1.bsp",
    ])

    def _resolve(self, start, end):
        spec = spice._MANIFEST["Europa Clipper"][1]
        with patch.object(spice, "_list_remote", return_value=self.LISTING):
            return [name for _, _, name in spice._resolve(spec, start, end)]

    def test_preliminary_and_noburn_arcs_are_never_loaded(self):
        names = self._resolve(datetime(2025, 4, 1), datetime(2025, 4, 5))
        self.assertTrue(all("PRELIM" not in n and "noburn" not in n for n in names), names)

    def test_arcs_are_ordered_by_data_cutoff_so_the_newest_wins(self):
        names = self._resolve(datetime(2025, 4, 1), datetime(2025, 4, 5))
        self.assertEqual(names, [
            "trj_250104-250614-dco2502250958-cruise005-final-OD042-v1.bsp",
            "trj_250318-250905-dco2505280203-cruise007-final-OD061-v1.bsp",
        ])

    def test_arcs_outside_the_requested_window_are_skipped(self):
        self.assertEqual(self._resolve(datetime(2025, 1, 5), datetime(2025, 1, 6)), [
            "trj_250104-250614-dco2502250958-cruise005-final-OD042-v1.bsp",
        ])


class FurnishOrderTests(unittest.TestCase):
    def test_generic_kernels_are_furnished_after_mission_kernels(self):
        # Mission SPKs bundle planetary segments (Juno's merge contains the Sun; Europa
        # Clipper's reference trajectory contains most of the solar system). SPICE prefers
        # the last kernel loaded, so de440s must come last or the observer's own position
        # changes depending on which spacecraft was requested alongside it.
        loaded = []
        fake = type("FakeSpice", (), {
            "kclear": staticmethod(lambda: loaded.clear()),
            "furnsh": staticmethod(loaded.append),
        })
        with patch.dict("sys.modules", {"spiceypy": fake}):
            spice.furnish([Path("/k/generic/de440s.bsp")], [Path("/k/Juno/spk_merge.bsp")])
        self.assertEqual([Path(p).name for p in loaded], ["spk_merge.bsp", "de440s.bsp"])

    def test_pool_is_cleared_so_repeated_calls_are_deterministic(self):
        loaded = []
        fake = type("FakeSpice", (), {
            "kclear": staticmethod(lambda: loaded.clear()),
            "furnsh": staticmethod(loaded.append),
        })
        with patch.dict("sys.modules", {"spiceypy": fake}):
            spice.furnish([Path("/k/generic/de440s.bsp")], [Path("/k/Juno/a.bsp")])
            spice.furnish([Path("/k/generic/de440s.bsp")], [Path("/k/Maven/b.bsp")])
        self.assertEqual([Path(p).name for p in loaded], ["b.bsp", "de440s.bsp"])


class PreferSpiceTests(unittest.TestCase):
    """prefer-spice must mix backends per body and say which produced what."""

    BODIES = ["Earth", "PSP", "ACE"]

    def points(self, names):
        return {n: [TrajectoryPoint(datetime(2025, 1, 1), 0.1, 0.01, 1.5e8)] for n in names}

    def test_bodies_without_kernels_fall_back_individually(self):
        from solarconflux import trajectories as traj

        def spice(names, *a, **k):
            # PSP has no NAIF mirror and ACE has no SPK at all.
            if names[0] in ("PSP", "ACE"):
                raise RuntimeError(f"no kernels for {names[0]}")
            return self.points(names)

        with patch.object(traj, "get_spice_trajectories", create=True):
            with patch("solarconflux.spice.get_spice_trajectories", side_effect=spice):
                with patch.object(traj, "_horizons_trajectories", side_effect=lambda n, *a, **k: self.points(n)):
                    result, provenance, _ = traj.retrieve_trajectories(
                        self.BODIES, "2025-01-01", "2025-01-02", "1d", source="prefer-spice"
                    )
        self.assertEqual(provenance, {"Earth": "spice", "PSP": "horizons", "ACE": "horizons"})

    def test_requested_body_order_is_preserved(self):
        from solarconflux import trajectories as traj

        def spice(names, *a, **k):
            if names[0] != "Earth":
                raise RuntimeError("no kernels")
            return self.points(names)

        with patch("solarconflux.spice.get_spice_trajectories", side_effect=spice):
            with patch.object(traj, "_horizons_trajectories", side_effect=lambda n, *a, **k: self.points(n)):
                result, _, _ = traj.retrieve_trajectories(
                    ["PSP", "Earth", "ACE"], "2025-01-01", "2025-01-02", "1d", source="prefer-spice"
                )
        self.assertEqual(list(result), ["PSP", "Earth", "ACE"])

    def test_alias_is_accepted(self):
        self.assertEqual(validate_source("spice-where-available"), "prefer-spice")
        self.assertEqual(validate_source("prefer-spice"), "prefer-spice")


class PreferSpicePartialCoverageTests(unittest.TestCase):
    """Preferring SPICE must never cost samples Horizons would have supplied.

    SOHO's archived SPK stops in 2014 while Horizons still covers it, so taking the SPICE
    result unconditionally silently discarded most of the requested window.
    """

    def series(self, count):
        start = datetime(2014, 11, 1)
        return [TrajectoryPoint(start + timedelta(days=i), 0.1, 0.01, 1.5e8) for i in range(count)]

    def retrieve(self, horizons_count):
        from solarconflux import trajectories as traj

        def spice(names, *a, **k):
            if names[0] == "SOHO":
                k["notes"]["SOHO"] = "truncated: kept the part within its SPICE coverage"
                return {"SOHO": self.series(31)}
            return {names[0]: self.series(93)}

        def horizons(names, *a, **k):
            return {name: self.series(horizons_count) for name in names}

        with patch("solarconflux.spice.get_spice_trajectories", side_effect=spice):
            with patch.object(traj, "_horizons_trajectories", side_effect=horizons):
                return traj.retrieve_trajectories(
                    ["Earth", "SOHO"], "2014-11-01", "2015-02-01", "1d", source="prefer-spice"
                )

    def test_a_longer_horizons_series_replaces_the_truncated_spice_one(self):
        trajectories, provenance, notes = self.retrieve(93)
        self.assertEqual(len(trajectories["SOHO"]), 93)
        self.assertEqual(provenance["SOHO"], "horizons")
        self.assertNotIn("SOHO", notes)

    def test_spice_is_kept_when_horizons_is_no_more_complete(self):
        trajectories, provenance, notes = self.retrieve(31)
        self.assertEqual(len(trajectories["SOHO"]), 31)
        self.assertEqual(provenance["SOHO"], "spice")
        self.assertIn("SPICE coverage", notes["SOHO"])

    def test_spice_results_survive_a_horizons_outage(self):
        from solarconflux import trajectories as traj

        def spice(names, *a, **k):
            if names[0] == "SOHO":
                k["notes"]["SOHO"] = "truncated: kept the part within its SPICE coverage"
                return {"SOHO": self.series(31)}
            return {names[0]: self.series(93)}

        with patch("solarconflux.spice.get_spice_trajectories", side_effect=spice):
            with patch.object(traj, "_horizons_trajectories", side_effect=OSError("network down")):
                trajectories, provenance, _ = traj.retrieve_trajectories(
                    ["Earth", "SOHO"], "2014-11-01", "2015-02-01", "1d", source="prefer-spice"
                )
        self.assertEqual(len(trajectories["SOHO"]), 31)
        self.assertEqual(provenance, {"Earth": "spice", "SOHO": "spice"})


class NoBodyCoveredTests(unittest.TestCase):
    """Dropping every uncovered body leaves nothing to screen, which must say why.

    The empty result used to surface downstream as a bare "At least one body must be
    selected", which reads as a bad request rather than a coverage gap.
    """

    def test_the_error_names_each_body_and_its_reason(self):
        from solarconflux import trajectories as traj

        def horizons(names, *a, **k):
            k["notes"].update({name: f"excluded: outside coverage for {name}" for name in names})
            return {}

        with patch.object(traj, "_horizons_trajectories", side_effect=horizons):
            with self.assertRaises(ValueError) as caught:
                traj.retrieve_trajectories(["Messenger", "PSP"], "2017-01-01", "2017-01-05", "1d")
        message = str(caught.exception)
        self.assertIn("None of the requested bodies have ephemeris coverage", message)
        self.assertIn("Messenger", message)
        self.assertIn("PSP", message)


class CoverageClampTests(unittest.TestCase):
    """Horizons names the edge of a mission's ephemeris; the window is clamped to it."""

    MESSAGE = ('No ephemeris for target "MESSENGER (spacecraft)" after '
               'A.D. 2015-MAY-01 18:49:57.1850 TDB')
    LAUNCH = ('No ephemeris for target "Parker Solar Probe (spacecraft)" prior to '
              'A.D. 2018-AUG-12 08:16:23.3431 TDB')

    def test_both_boundary_messages_are_parsed(self):
        from solarconflux.trajectories import _parse_coverage_limit

        self.assertEqual(_parse_coverage_limit(self.MESSAGE), ("end", datetime(2015, 5, 1, 18, 49, 57)))
        self.assertEqual(_parse_coverage_limit(self.LAUNCH), ("start", datetime(2018, 8, 12, 8, 16, 23)))
        self.assertIsNone(_parse_coverage_limit("some unrelated Horizons failure"))

    def test_window_is_clamped_onto_the_original_grid(self):
        from solarconflux.trajectories import _clamp_to_grid

        # Daily samples from 2015-04-28 and coverage ending 2015-05-01 18:49 leave
        # 2015-05-01 as the last usable sample, which must stay on the daily grid.
        self.assertEqual(
            _clamp_to_grid(datetime(2015, 4, 28), datetime(2015, 5, 4), 86400.0,
                           "end", datetime(2015, 5, 1, 18, 49, 57)),
            (datetime(2015, 4, 28), datetime(2015, 5, 1)),
        )

    def test_no_overlap_reports_nothing_usable(self):
        from solarconflux.trajectories import _clamp_to_grid

        self.assertEqual(
            _clamp_to_grid(datetime(2017, 1, 1), datetime(2017, 1, 5), 86400.0,
                           "start", datetime(2018, 8, 12, 8, 16, 23)),
            (None, None),
        )

    def test_alignment_ends_when_a_body_loses_coverage(self):
        from solarconflux.geometries import Geometry

        full = [TrajectoryPoint(datetime(2025, 1, 1 + i), 0.0, 0.0, 1.5e8) for i in range(4)]
        short = [TrajectoryPoint(datetime(2025, 1, 1 + i), 0.0, 0.0, 1.0e8) for i in range(2)]
        events = Geometry(["Earth", "Venus", "Messenger"],
                          {"Earth": full, "Venus": list(full), "Messenger": short}).check_geometry("cone")
        spans = {tuple(e.group): (e.start_time, e.end_time) for e in events}
        self.assertEqual(spans[("Earth", "Messenger", "Venus")][1], "2025-01-02 00:00:00")
        self.assertEqual(spans[("Earth", "Venus")][1], "2025-01-04 00:00:00")


class TimestampSnapTests(unittest.TestCase):
    """Horizons timestamps carry ~100 us of noise; a SPICE grid is exact.

    Geometry demands every body share a timestamp exactly, so without snapping, a mixed
    run fails with "All trajectories must have matching timestamps at each step."
    """

    def test_sub_millisecond_noise_is_snapped_to_the_second(self):
        from solarconflux.geometries import _snap_to_second

        self.assertEqual(_snap_to_second(datetime(2025, 1, 1, 6, 0, 0, 101)), datetime(2025, 1, 1, 6, 0))
        self.assertEqual(_snap_to_second(datetime(2025, 1, 1, 5, 59, 59, 999950)), datetime(2025, 1, 1, 6, 0))

    def test_genuine_sub_second_sampling_is_preserved(self):
        from solarconflux.geometries import _snap_to_second

        half = datetime(2025, 1, 1, 6, 0, 0, 500000)
        self.assertEqual(_snap_to_second(half), half)

    def test_mixed_backend_timestamps_build_a_valid_geometry(self):
        from solarconflux.geometries import Geometry

        class FakeCoord:
            def __init__(self, moment):
                self.obstime = type("T", (), {"datetime": moment})()
                self.spherical = type("S", (), {"lon": 0.1, "lat": 0.01, "distance": 1.5e8})()

        base = datetime(2025, 1, 1)
        noisy = [FakeCoord(base.replace(microsecond=101)), FakeCoord(base.replace(hour=6, microsecond=93))]
        exact = [FakeCoord(base), FakeCoord(base.replace(hour=6))]
        Geometry(["A", "B"], {"A": noisy, "B": exact})


class BundleProvenanceTests(unittest.TestCase):
    def _bundle(self, source):
        when = datetime(2025, 1, 1)
        data = {"Earth": [TrajectoryPoint(when, 0.1, 0.01, 1.5e8)]}
        return trajectory_bundle(data, "2025-01-01", "2025-01-02", "1d", source=source)

    def test_source_label_records_the_backend_used(self):
        self.assertIn("Horizons", self._bundle("horizons")["source"])
        self.assertIn("SPICE", self._bundle("spice")["source"])
        mixed = self._bundle("prefer-spice")["source"]
        self.assertIn("SPICE", mixed)
        self.assertIn("Horizons", mixed)

    def test_per_body_provenance_is_recorded_when_given(self):
        when = datetime(2025, 1, 1)
        data = {"Earth": [TrajectoryPoint(when, 0.1, 0.01, 1.5e8)],
                "PSP": [TrajectoryPoint(when, 0.2, 0.02, 1.0e8)]}
        bundle = trajectory_bundle(data, "2025-01-01", "2025-01-02", "1d", source="prefer-spice",
                                  provenance={"Earth": "spice", "PSP": "horizons"})
        self.assertEqual(bundle["body_sources"], {"Earth": "spice", "PSP": "horizons"})

    def test_provenance_is_omitted_when_not_supplied(self):
        self.assertNotIn("body_sources", self._bundle("horizons"))

    def test_default_remains_horizons(self):
        when = datetime(2025, 1, 1)
        data = {"Earth": [TrajectoryPoint(when, 0.1, 0.01, 1.5e8)]}
        bundle = trajectory_bundle(data, "2025-01-01", "2025-01-02", "1d")
        self.assertIn("Horizons", bundle["source"])


if __name__ == "__main__":
    unittest.main()
