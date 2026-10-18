import unittest
from datetime import datetime,timezone,timedelta
from incident_correlation import correlate,overview

NOW=datetime(2026,10,16,12,0,tzinfo=timezone.utc)
def event(minutes,state='failed'):
    return {'at':(NOW-timedelta(minutes=minutes)).isoformat(),'state':state,'kind':'probe'}
class CorrelationTests(unittest.TestCase):
    def test_recurrence(self):self.assertTrue(correlate([event(1),event(2),event(3)],now=NOW)['recurrent'])
    def test_old_and_future_ignored(self):self.assertEqual(correlate([event(31),event(-1),event(0)],now=NOW)['count'],1)
    def test_unknown_not_error(self):self.assertFalse(correlate([event(1,'unknown')]*3,now=NOW)['recurrent'])
    def test_bad_date(self):self.assertEqual(correlate([{'at':'oops','state':'failed'}],now=NOW)['count'],0)
    def test_threshold(self):self.assertTrue(correlate([event(1),event(2)],threshold=2,now=NOW)['recurrent'])
    def test_validation(self):
        with self.assertRaises(ValueError):correlate([],window_minutes=0)
        with self.assertRaises(ValueError):correlate([],threshold=1)
    def test_overview(self):
        probes=[('a','tcp_local','failed',(NOW-timedelta(minutes=i)).isoformat()) for i in (1,2,3)]
        rows=overview([{'id':'a','name':'Serveur A'},{'id':'b','name':'Serveur B'}],[],probes,now=NOW)
        self.assertEqual([(r['id'],r['count']) for r in rows],[('a',3)])
