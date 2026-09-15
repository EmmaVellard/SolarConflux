"""Run explicitly with SOLARCONFLUX_RUN_HTTP_TESTS=1; opens a loopback test server."""
import json
import os
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from solarconflux.server import create_server

@unittest.skipUnless(os.environ.get('SOLARCONFLUX_RUN_HTTP_TESTS')=='1','Set SOLARCONFLUX_RUN_HTTP_TESTS=1 for loopback HTTP tests.')
class HttpTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.server=create_server('127.0.0.1',0,self.directory.name,['https://emmavellard.github.io'])
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_address[1]}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.directory.cleanup()
    def test_allowed_origin_receives_json_and_cors(self):
        payload={'bodies':['Earth','Venus'],'start':'2025-01-01','end':'2025-01-02','step':'6h'}
        req=Request(self.base+'/api/trajectories',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Origin':'https://emmavellard.github.io'})
        with patch('solarconflux.server.retrieve',return_value=b'{"schema":"test"}') as fetch:
            with urlopen(req,timeout=5) as res:
                self.assertEqual(res.status,200);self.assertEqual(res.headers['Access-Control-Allow-Origin'],'https://emmavellard.github.io');self.assertEqual(json.load(res)['schema'],'test')
            fetch.assert_called_once_with(payload)
    def test_unapproved_origin_is_rejected_before_retrieval(self):
        req=Request(self.base+'/api/trajectories',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://unapproved.example'})
        with patch('solarconflux.server.retrieve') as fetch:
            with self.assertRaises(HTTPError) as error:urlopen(req,timeout=5)
            self.assertEqual(error.exception.code,403);fetch.assert_not_called()
    def test_rejects_arbitrary_endpoint_and_invalid_media(self):
        for path,headers,status in [('/api/arbitrary',{},404),('/api/trajectories',{'Content-Type':'text/plain'},415)]:
            with self.subTest(path=path),self.assertRaises(HTTPError) as error:urlopen(Request(self.base+path,data=b'{}',headers=headers),timeout=5)
            self.assertEqual(error.exception.code,status)
    def test_health_is_not_dependent_on_horizons(self):
        with urlopen(self.base+'/api/health',timeout=5) as res:self.assertEqual(json.load(res)['status'],'ready')
