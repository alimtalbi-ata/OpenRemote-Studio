"""V10.3 regression tests. Author Abdelhalim Talbi."""
import unittest
from ssh_diagnostic_history import percentile,trends

def entry(ms,state='ok'):
    return {'report':{'schema':'openremote.ssh-diagnostic.v1','status':'failed' if state=='failed' else 'authenticated','steps':[{'step':'Bastion principal','state':state,'duration_ms':ms}]}}

class TestHistoryV103(unittest.TestCase):
    def test_empty(self):self.assertEqual(trends([]),[])
    def test_p95(self):self.assertEqual(percentile(list(range(1,101)),95),95)
    def test_median(self):self.assertEqual(percentile([1,2,3,4],50),2)
    def test_single(self):self.assertEqual(percentile([99],95),99)
    def test_invalid_values(self):
        for values in ([float('nan')],[float('inf')],[-1],[True]):
            with self.subTest(values=values),self.assertRaises(ValueError):percentile(values,95)
    def test_invalid_percent(self):
        for p in (0,101,True):
            with self.subTest(p=p),self.assertRaises(ValueError):percentile([1],p)
    def test_aggregates(self):
        result=trends([entry(100),entry(300,'failed')])[0]
        self.assertEqual((result['runs'],result['failures'],result['failure_rate_pct']), (2,1,50.0))
        self.assertEqual((result['average_ms'],result['median_ms'],result['p95_ms']),(200,100,300))
    def test_no_durations(self):
        row=entry(None)
        result=trends([row])[0]
        self.assertIsNone(result['median_ms']);self.assertIsNone(result['p95_ms'])
    def test_immutable_inputs(self):
        values=[3,1,2];percentile(values,95);self.assertEqual(values,[3,1,2])
    def test_qt_dashboard_columns(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'ssh_history_dashboard.py').read_text()
        self.assertIn('P95 (ms)',source);self.assertIn('failure_rate_pct',source)
