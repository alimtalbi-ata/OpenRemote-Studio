import unittest
from datetime import datetime,timezone,timedelta
from incident_trends import build_trends
class TrendsTests(unittest.TestCase):
    def setUp(self): self.now=datetime(2026,10,16,16,tzinfo=timezone.utc)
    def event(self,minutes,identity='a',kind='tcp_local',state='failed'):
        return (identity,kind,state,(self.now-timedelta(minutes=minutes)).isoformat())
    def test_empty(self):
        r=build_trends([],[],'a',now=self.now)
        self.assertEqual(r['total_errors'],0);self.assertEqual(len(r['buckets']),4)
    def test_split(self):
        r=build_trends([], [self.event(50),self.event(10),self.event(9)],'a',now=self.now)
        self.assertEqual((r['earlier_half'],r['later_half'],r['delta']),(1,2,1))
    def test_no_cross_connection(self):
        self.assertEqual(build_trends([], [self.event(10,'b')],'a',now=self.now)['total_errors'],0)
    def test_no_success(self):
        self.assertEqual(build_trends([], [self.event(10,state='ok')],'a',now=self.now)['total_errors'],0)
    def test_future_ignored(self):
        self.assertEqual(build_trends([], [self.event(-5)],'a',now=self.now)['total_errors'],0)
    def test_old_ignored(self):
        self.assertEqual(build_trends([], [self.event(70)],'a',now=self.now)['total_errors'],0)
    def test_session(self):
        s={'connection_id':'a','finished_at':self.event(5)[3],'exit_code':1}
        self.assertEqual(build_trends([s],[],'a',now=self.now)['total_errors'],1)
    def test_bucket_totals(self):
        r=build_trends([], [self.event(3),self.event(4,kind='ssh_jump')],'a',now=self.now)
        self.assertEqual(sum(b['total'] for b in r['buckets']),2)
    def test_invalid_window(self):
        with self.assertRaises(ValueError):build_trends([],[],'a',minutes=45)
    def test_invalid_bucket(self):
        with self.assertRaises(ValueError):build_trends([],[],'a',bucket_minutes=7)
    def test_naive_clock(self):
        with self.assertRaises(ValueError):build_trends([],[],'a',now=datetime(2026,1,1))
    def test_no_remote_claim(self):
        self.assertFalse(build_trends([],[],'a',now=self.now)['remote_cause_confirmed'])
    def test_no_identity_leak(self):
        self.assertNotIn('secret-host',str(build_trends([],[],'secret-host',now=self.now)))
