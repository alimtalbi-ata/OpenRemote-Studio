import unittest
from datetime import datetime, timezone, timedelta
from dependency_temporal import compare_temporal

NOW=datetime(2026,10,16,12,0,tzinfo=timezone.utc)
C=[{'id':'a'},{'id':'b'},{'id':'c'}]
ROUTE={'mode':'ssh_jump','jump_host':'jump.example','jump_port':22,'jump_chain':''}
ROUTES={i['id']:ROUTE for i in C}
DASH={'rows':[{'id':i['id'],'local_errors_30m':1} for i in C]}
def probe(identity,sec):
    return (identity,'tcp_local','failed',(NOW-timedelta(seconds=sec)).isoformat())

class TemporalTests(unittest.TestCase):
    def run_report(self,probes,**kwargs):
        return compare_temporal(C,ROUTES,DASH,[],probes,now=NOW,**kwargs)
    def test_simultaneous(self):
        g=self.run_report([probe('a',120),probe('b',100)])['groups'][0]
        self.assertEqual(g['overlap_windows'],1)
        self.assertEqual(g['max_simultaneous_connections'],2)
        self.assertEqual(g['overlapping_connection_ids'],['a','b'])
    def test_separated(self):
        self.assertEqual(self.run_report([probe('a',300),probe('b',100)])['groups'][0]['overlap_windows'],0)
    def test_same_connection_not_overlap(self):
        self.assertEqual(self.run_report([probe('a',120),probe('a',110)])['groups'][0]['overlap_windows'],0)
    def test_outside_window(self):
        self.assertEqual(self.run_report([probe('a',1900),probe('b',1890)])['groups'][0]['observed_error_events'],0)
    def test_future_ignored(self):
        self.assertEqual(self.run_report([probe('a',-20),probe('b',-30)])['groups'][0]['overlap_windows'],0)
    def test_no_transitive_chaining(self):
        g=self.run_report([probe('a',180),probe('b',130),probe('c',80)])['groups'][0]
        self.assertEqual(g['max_simultaneous_connections'],2)
    def test_invalid_window(self):
        with self.assertRaises(ValueError):self.run_report([],minutes=0)
    def test_invalid_tolerance(self):
        with self.assertRaises(ValueError):self.run_report([],tolerance_seconds=-1)
    def test_naive_time(self):
        with self.assertRaises(ValueError):compare_temporal(C,ROUTES,DASH,[],[],now=datetime(2026,1,1))
    def test_no_remote_claim(self):
        r=self.run_report([probe('a',120),probe('b',100)])
        self.assertFalse(r['remote_cause_confirmed'])
        self.assertFalse(r['groups'][0]['remote_cause_confirmed'])
    def test_empty(self):
        self.assertEqual(self.run_report([])['groups'][0]['overlap_windows'],0)
    def test_bad_route_skipped(self):
        r=compare_temporal(C,{'a':{'mode':'invalid'}},DASH,[],[],now=NOW)
        self.assertEqual(r['groups'],[])
