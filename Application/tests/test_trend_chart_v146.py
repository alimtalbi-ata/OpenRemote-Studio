import unittest
from trend_chart_data import chart_data,stacked_heights

class TrendChartTests(unittest.TestCase):
    def report(self,points=((1,2,3),(0,0,0))):
        return {'schema':'openremote.incident_trends.v1','scope':'local_only','remote_cause_confirmed':False,
                'buckets':[{'counts':dict(zip(('tcp_local','ssh_jump','session_exit'),p)),'total':sum(p)} for p in points]}
    def test_series(self):self.assertEqual(chart_data(self.report())['total'],6)
    def test_empty(self):self.assertEqual(chart_data(self.report(((0,0,0),)))['maximum'],1)
    def test_bad_schema(self):
        with self.assertRaises(ValueError):chart_data({'schema':'x'})
    def test_bad_scope(self):
        r=self.report();r['scope']='remote'
        with self.assertRaises(ValueError):chart_data(r)
    def test_bad_counts(self):
        r=self.report();r['buckets'][0]['counts']['tcp_local']=-1
        with self.assertRaises(ValueError):chart_data(r)
    def test_inconsistent_total(self):
        r=self.report();r['buckets'][0]['total']=99
        with self.assertRaises(ValueError):chart_data(r)
    def test_invalid_empty_buckets(self):
        r=self.report();r['buckets']=[]
        with self.assertRaises(ValueError):chart_data(r)
    def test_heights(self):self.assertEqual(stacked_heights((1,2,3),6,60),(10,20,30))
    def test_rounding(self):self.assertEqual(sum(stacked_heights((1,1,1),3,100)),100)
    def test_overflow(self):
        with self.assertRaises(ValueError):stacked_heights((2,2,2),5,100)
    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):stacked_heights((True,0,0),1,10)
