import copy
import csv
import io
import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from solarconflux.browser import load_bundle, screen_bundle, save_trajectory_bundle
from solarconflux.events import MatchEntry, format_timestamp
from solarconflux.export import save_match
from solarconflux.geometries import Geometry, TrajectoryPoint
from solarconflux.validation import validate_date_range
from solarconflux.cli import build_parser, run_from_args

ROOT = Path(__file__).resolve().parents[1]

class IntegrityTests(unittest.TestCase):
    def points(self):
        return {name: [TrajectoryPoint(datetime(2025,1,1)+timedelta(hours=i),0,0,1e8) for i in range(3)] for name in ['Earth','Venus']}

    def test_misaligned_timestamps_are_rejected(self):
        t=self.points(); t['Venus'][1]=TrajectoryPoint(datetime(2025,1,2),0,0,1e8)
        with self.assertRaisesRegex(ValueError,'matching timestamps'):
            Geometry(t.keys(),t)

    def test_unsorted_timestamps_are_rejected(self):
        t=self.points()
        for k in t: t[k].reverse()
        with self.assertRaisesRegex(ValueError,'strictly increasing'):
            Geometry(t.keys(),t)

    def test_nonfinite_coordinates_are_rejected(self):
        for lon,lat,radius in [(math.nan,0,1),(0,math.inf,1),(0,0,-1),(0,2,1),(0,0,math.inf)]:
            with self.subTest(lon=lon,lat=lat,radius=radius):
                with self.assertRaises(ValueError):
                    Geometry(['Earth'],{'Earth':[TrajectoryPoint(datetime(2025,1,1),lon,lat,radius)]})

    def test_only_selected_bodies_are_screened(self):
        t=self.points(); t['Mars']=t['Earth']
        self.assertEqual(Geometry(['Earth','Venus'],t).check_geometry('cone')[0].group,['Earth','Venus'])

    def test_folder_covers_longest_overlapping_event(self):
        with tempfile.TemporaryDirectory() as temp:
            output=save_match({'cone':[MatchEntry('2025-01-01 00:00:00','2025-01-15 00:00:00',['Earth','Venus'])], 'quadrature':[MatchEntry('2025-01-02 00:00:00','2025-01-03 00:00:00',['Earth','Mars'])]},temp)
            self.assertEqual(output.parent.name,'2025-01-01_to_2025-01-15')

    def test_timestamp_rounding_and_utc(self):
        self.assertEqual(format_timestamp(datetime(2025,1,14,23,59,59,999702)),'2025-01-15 00:00:00')
        self.assertEqual(format_timestamp(datetime(2025,1,1,1,tzinfo=timezone(timedelta(hours=1)))),'2025-01-01 00:00:00')
        validate_date_range('2025-01-01Z','2025-01-02')

    def test_invalid_cli_parameter_fails_before_network(self):
        args=build_parser().parse_args(['--bodies','Earth,Venus','--start-time','2025-01-01','--end-time','2025-01-02','--geometries','cone','--cone-width','-1'])
        with patch('solarconflux.cli.get_trajectories') as fetch:
            with self.assertRaises(ValueError): run_from_args(args)
            fetch.assert_not_called()

class BrowserBridgeTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'web/example.json').read_text())
        self.config={'bodies':['Earth','Solar Orbiter','BepiColombo'],'modes':['cone','parker','coneparker','opposition','quadrature','arbitrary'],'start':'2025-01-01T00:00:00Z','end':'2025-01-15T00:00:00Z','cone':20,'tolerance':15,'latitude':10,'speed':400,'angle':30}

    def test_real_bundle_reference_and_csv(self):
        result=screen_bundle(self.data,self.config)
        cone=[e for e in result['events'] if e['geometry']=='cone']
        self.assertEqual(len(cone),1)
        self.assertEqual(cone[0]['bodies'],'Earth;Solar Orbiter')
        self.assertEqual(cone[0]['duration_hours'],'336')
        self.assertEqual(result['metadata']['sample_count_per_body'],57)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(result['csv'])))),len(result['events']))
        self.assertFalse(any(e['geometry']=='parker' for e in result['events']))

    def test_roundtrip_trajectory_export(self):
        with tempfile.TemporaryDirectory() as temp:
            path=save_trajectory_bundle(load_bundle(self.data),Path(temp)/'trajectories.json','2025-01-01','2025-01-15','6h')
            result=load_bundle(json.loads(path.read_text()))
            self.assertEqual(len(result['Earth']),57)
            self.assertAlmostEqual(result['Earth'][0].radius_km,147107542.05561554)

    def test_import_rejects_wrong_frame_gaps_and_nan(self):
        for kind in ['frame','gap','nan','time']:
            data=copy.deepcopy(self.data)
            if kind=='frame': data['frame']='HeliographicStonyhurst'
            if kind=='gap':
                for points in data['trajectories'].values(): del points[1]
            if kind=='nan': data['trajectories']['Earth'][0]['lon_deg']=float('nan')
            if kind=='time': data['trajectories']['Earth'][0]['time']='invalid'
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError): load_bundle(data)

    def test_empty_results_still_have_csv_headers(self):
        self.config.update(modes=['opposition'],tolerance=0)
        result=screen_bundle(self.data,self.config)
        self.assertEqual(result['events'],[])
        self.assertIn('event_id,start_time',result['csv'])

    def test_single_sample_has_zero_duration(self):
        self.config['end']=self.config['start']; self.config['modes']=['cone']
        result=screen_bundle(self.data,self.config)
        self.assertEqual(result['events'][0]['duration_hours'],'0')

    def test_range_beyond_coverage_is_rejected(self):
        self.config['end']='2026-01-01'
        with self.assertRaisesRegex(ValueError,'coverage'): screen_bundle(self.data,self.config)

    def test_subset_does_not_include_unselected_body(self):
        self.config['bodies']=['Earth','Solar Orbiter']
        result=screen_bundle(self.data,self.config)
        self.assertTrue(all('BepiColombo' not in e['bodies'] for e in result['events']))

if __name__=='__main__': unittest.main()
