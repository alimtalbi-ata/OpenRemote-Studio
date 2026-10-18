import unittest
from datetime import datetime,timezone,timedelta
from operations_dashboard import build_dashboard
class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,16,12,tzinfo=timezone.utc)
        self.c=[{'id':'a','name':'Sensitive Host','protocol':'SSH'},{'id':'b','protocol':'RDP'}]
    def test_empty(self):
        r=build_dashboard([],[],[],now=self.now)
        self.assertEqual(r['connections'],0)
    def test_no_observations(self):
        r=build_dashboard(self.c,[],[],now=self.now)
        self.assertEqual(r['without_observations'],2)
    def test_protocols(self):
        self.assertEqual(build_dashboard(self.c,[],[],now=self.now)['protocols'],{'RDP':1,'SSH':1})
    def test_privacy(self):
        self.assertNotIn('Sensitive Host',str(build_dashboard(self.c,[],[],now=self.now)))
    def test_recent_failures(self):
        t=(self.now-timedelta(minutes=5)).isoformat()
        probes=[('a','tcp_local','failed',t)]*3
        r=build_dashboard(self.c,[],probes,now=self.now)
        self.assertEqual(r['recurrent_local_failures'],1)
        self.assertEqual(r['rows'][0]['id'],'a')
    def test_unknown_not_failure(self):
        t=self.now.isoformat()
        r=build_dashboard(self.c,[],[('a','tcp_local','unknown',t)],now=self.now)
        self.assertEqual(r['recurrent_local_failures'],0)
    def test_remote_unverified(self):
        self.assertIs(build_dashboard(self.c,[],[],now=self.now)['remote_health_verified'],False)
    def test_reject_bad_inputs(self):
        with self.assertRaises(ValueError):build_dashboard({},[],[])
    def test_unrecognized_protocol(self):
        self.assertEqual(build_dashboard([{'id':'x','protocol':'other'}],[],[],now=self.now)['protocols'],{'OTHER':1})
