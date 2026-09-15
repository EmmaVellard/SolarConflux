import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from solarconflux import server
from solarconflux.geometries import Geometry, TrajectoryPoint

class RetrievalServiceTests(unittest.TestCase):
    def setUp(self):
        server._CACHE.clear(); server._CACHE_BYTES=0; server._BACKOFF_UNTIL=0
        self.request={'bodies':['Earth','Venus'],'start':'2025-01-01T00:00:00Z','end':'2025-01-02T00:00:00Z','step':'6h'}

    def data(self,names,*args):
        return {name:[TrajectoryPoint(datetime(2025,1,1)+timedelta(hours=i*6),.1,.01,1e8) for i in range(5)] for name in names}

    def test_rejects_unknown_bodies_and_arbitrary_upstream_parameters(self):
        for update in ({'bodies':['Earth','unlisted']},{'url':'https://example.com'},{'bodies':'Earth,Venus'},{'step':'0h'}):
            with self.subTest(update=update), self.assertRaises(ValueError): server.validate_request({**self.request,**update})

    def test_limits_range_sample_count_and_spacing(self):
        for update in ({'start':'2025-02-01'},{'end':'2200-01-01'},{'end':'2025-01-02T01:00:00Z'},{'end':'2026-01-01','step':'1h'}):
            with self.subTest(update=update), self.assertRaises(ValueError): server.validate_request({**self.request,**update})

    def test_caches_identical_request_regardless_of_body_order(self):
        with patch.object(server,'get_trajectories',side_effect=self.data) as fetch:
            a=server.retrieve(self.request)
            b=server.retrieve({**self.request,'bodies':['Venus','Earth']})
            self.assertEqual(a,b); self.assertEqual(fetch.call_count,1)
            self.assertEqual(json.loads(a)['frame'],'HeliocentricInertial')

    def test_sun_is_constructed_as_origin_without_query(self):
        with patch.object(server,'get_trajectories',side_effect=self.data) as fetch:
            data=json.loads(server.retrieve({**self.request,'bodies':['Earth','Venus','Sun']}))
            self.assertEqual(fetch.call_args.args[0],['Earth','Venus'])
            self.assertEqual(data['trajectories']['Sun'][0]['radius_km'],0)

    def test_sun_does_not_create_spurious_alignment_groups(self):
        when=datetime(2025,1,1)
        data={'Sun':[TrajectoryPoint(when,0,0,0)],'Earth':[TrajectoryPoint(when,.05,0,1e8)],'Venus':[TrajectoryPoint(when,-.05,0,1e8)]}
        events=Geometry(data.keys(),data).check_geometry('cone')
        self.assertEqual(events[0].group,['Earth','Venus'])

    def test_query_lock_prevents_concurrent_horizons_calls(self):
        server._QUERY_LOCK.acquire()
        try:
            with patch.object(server,'get_trajectories') as fetch:
                with self.assertRaises(server.ServiceBusy): server.retrieve(self.request)
                fetch.assert_not_called()
        finally: server._QUERY_LOCK.release()

    def test_failure_does_not_cache_or_immediately_retry(self):
        with patch.object(server,'get_trajectories',side_effect=RuntimeError('Horizons query failed for Messenger')) as fetch:
            with self.assertRaisesRegex(RuntimeError,'Messenger'): server.retrieve(self.request)
            with self.assertRaises(server.ServiceBusy): server.retrieve(self.request)
            self.assertEqual(fetch.call_count,1);self.assertFalse(server._CACHE)

if __name__=='__main__': unittest.main()
