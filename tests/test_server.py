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

    def data(self,names,*args,**kwargs):
        source=kwargs.get('source','horizons')
        return ({name:[TrajectoryPoint(datetime(2025,1,1)+timedelta(hours=i*6),.1,.01,1e8) for i in range(5)] for name in names},
                {name:source for name in names}, {})

    def test_rejects_unknown_bodies_and_arbitrary_upstream_parameters(self):
        for update in ({'bodies':['Earth','unlisted']},{'url':'https://example.com'},{'bodies':'Earth,Venus'},{'step':'0h'}):
            with self.subTest(update=update), self.assertRaises(ValueError): server.validate_request({**self.request,**update})

    def test_limits_range_sample_count_and_spacing(self):
        for update in ({'start':'2025-02-01'},{'end':'2200-01-01'},{'end':'2025-01-02T01:00:00Z'},{'end':'2026-01-01','step':'1h'}):
            with self.subTest(update=update), self.assertRaises(ValueError): server.validate_request({**self.request,**update})

    def test_caches_identical_request_regardless_of_body_order(self):
        with patch.object(server,'retrieve_trajectories',side_effect=self.data) as fetch:
            a=server.retrieve(self.request)
            b=server.retrieve({**self.request,'bodies':['Venus','Earth']})
            self.assertEqual(a,b); self.assertEqual(fetch.call_count,1)
            self.assertEqual(json.loads(a)['frame'],'HeliocentricInertial')

    def test_sun_is_constructed_as_origin_without_query(self):
        with patch.object(server,'retrieve_trajectories',side_effect=self.data) as fetch:
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
            with patch.object(server,'retrieve_trajectories') as fetch:
                with self.assertRaises(server.ServiceBusy): server.retrieve(self.request)
                fetch.assert_not_called()
        finally: server._QUERY_LOCK.release()

    def test_outage_does_not_cache_and_backs_off(self):
        outage=RuntimeError('Horizons unreachable'); outage.__cause__=ConnectionResetError('reset')
        with patch.object(server,'retrieve_trajectories',side_effect=outage) as fetch:
            with self.assertRaisesRegex(RuntimeError,'unreachable'): server.retrieve(self.request)
            with self.assertRaises(server.ServiceBusy): server.retrieve(self.request)
            self.assertEqual(fetch.call_count,1);self.assertFalse(server._CACHE)

    def test_bad_request_failure_does_not_block_other_requests(self):
        # A body/date error is deterministic, so it must not trigger the shared backoff.
        with patch.object(server,'retrieve_trajectories',side_effect=RuntimeError('Horizons query failed for Messenger')) as fetch:
            with self.assertRaisesRegex(RuntimeError,'Messenger'): server.retrieve(self.request)
            with self.assertRaisesRegex(RuntimeError,'Messenger'): server.retrieve(self.request)
            self.assertEqual(fetch.call_count,2);self.assertFalse(server._CACHE)

    def test_source_is_accepted_defaulted_and_validated(self):
        self.assertEqual(server.validate_request(self.request)['source'],'horizons')
        self.assertEqual(server.validate_request({**self.request,'source':'spice'})['source'],'spice')
        with self.assertRaisesRegex(ValueError,'Unsupported trajectory source'): server.validate_request({**self.request,'source':'cspice'})

    def test_source_is_passed_through_and_separates_cache_entries(self):
        with patch.object(server,'retrieve_trajectories',side_effect=self.data) as fetch:
            server.retrieve({**self.request,'source':'spice'})
            self.assertEqual(fetch.call_args.kwargs['source'],'spice')
            server.retrieve({**self.request,'source':'horizons'})
            self.assertEqual(fetch.call_count,2)

    def test_rejected_body_is_a_bad_request_not_a_gateway_error(self):
        with patch.object(server,'retrieve_trajectories',side_effect=ValueError('ACE cannot be retrieved from SPICE kernels.')):
            with self.assertRaisesRegex(ValueError,'ACE'): server.retrieve({**self.request,'source':'spice'})
            self.assertEqual(server._BACKOFF_UNTIL,0)

if __name__=='__main__': unittest.main()
