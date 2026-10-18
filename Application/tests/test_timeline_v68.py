import unittest
from connection_timeline import timeline,export_timeline

class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.sessions=[dict(connection_id='a',protocol='SSH',started_at='2026-10-01T10:00:00+00:00',finished_at='2026-10-01T10:02:00+00:00',exit_code=255),dict(connection_id='b',protocol='RDP',started_at='2026-10-01T09:00:00Z',finished_at=None,exit_code=None)]
        self.probes=[('a','tcp_local','failed','2026-10-01T10:01:00Z'),('b','ssh_jump','ok','2026-10-01T10:03:00Z')]
    def test_merge_and_order(self):
        rows=timeline(self.sessions,self.probes,'a');self.assertEqual([r['state'] for r in rows],['error','failed','started'])
    def test_filter(self):
        self.assertEqual(len(timeline(self.sessions,self.probes,'a',kind='error')),2)
        self.assertEqual(len(timeline(self.sessions,self.probes,'a',kind='probe')),1)
    def test_isolation(self):self.assertEqual(len(timeline(self.sessions,self.probes,'b')),2)
    def test_limit(self):self.assertEqual(len(timeline(self.sessions,self.probes,'a',limit=1)),1)
    def test_invalid(self):
        with self.assertRaises(ValueError):timeline([],[],'a',limit=0)
        with self.assertRaises(ValueError):timeline([],[],'a',kind='bad')
    def test_csv_no_secrets(self):
        csv=export_timeline(timeline(self.sessions,self.probes,'a'))
        self.assertIn('utc,category,state,detail',csv);self.assertNotIn('password',csv)
    def test_invalid_timestamps(self):
        self.assertEqual(timeline([dict(connection_id='a',started_at='invalid',finished_at=None)],[],'a'),[])
