import unittest
from datetime import datetime,timezone,timedelta
from local_incident_groups import group_local_errors,format_summary

class LocalGroupsTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,16,16,tzinfo=timezone.utc)
        self.stamp=(self.now-timedelta(minutes=10)).isoformat()
    def test_empty(self):
        self.assertEqual(group_local_errors([],[],'x',now=self.now)['total_errors'],0)
    def test_tcp_group(self):
        r=group_local_errors([], [('x','tcp_local','failed',self.stamp)]*3,'x',now=self.now)
        self.assertEqual(r['groups'][0]['count'],3)
    def test_ssh_group(self):
        r=group_local_errors([], [('x','ssh_jump','failed',self.stamp)],'x',now=self.now)
        self.assertEqual(r['groups'][0]['category'],'ssh_jump')
    def test_sessions(self):
        r=group_local_errors([{'connection_id':'x','finished_at':self.stamp,'exit_code':1}],[],'x',now=self.now)
        self.assertEqual(r['groups'][0]['category'],'session_exit')
    def test_no_remote_inference(self):
        self.assertFalse(group_local_errors([],[],'x',now=self.now)['remote_cause_confirmed'])
    def test_other_connection_ignored(self):
        self.assertEqual(group_local_errors([], [('y','tcp_local','failed',self.stamp)],'x',now=self.now)['total_errors'],0)
    def test_outside_window(self):
        old=(self.now-timedelta(hours=4)).isoformat()
        self.assertEqual(group_local_errors([], [('x','tcp_local','failed',old)],'x',now=self.now)['total_errors'],0)
    def test_future_ignored(self):
        future=(self.now+timedelta(minutes=2)).isoformat()
        self.assertEqual(group_local_errors([], [('x','tcp_local','failed',future)],'x',now=self.now)['total_errors'],0)
    def test_no_host_secret(self):
        r=group_local_errors([], [('x','tcp_local','failed',self.stamp)],'x',now=self.now)
        self.assertNotIn('x',str(r['groups']))
    def test_summary(self):
        r=group_local_errors([],[],'x',now=self.now)
        self.assertIn('non vérifiée',format_summary(r))
    def test_invalid_window(self):
        with self.assertRaises(ValueError):group_local_errors([],[],'x',now=self.now,minutes=0)
    def test_invalid_id(self):
        with self.assertRaises(ValueError):group_local_errors([],[],'',now=self.now)
