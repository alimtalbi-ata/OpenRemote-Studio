"""V10.4 SSH latency alert regression tests."""
import unittest
from ssh_latency_alerts import evaluate,evaluate_dashboard,STEPS

def series(*values):return [{'duration_ms':v} for v in values]
class TestLatencyAlerts(unittest.TestCase):
    def test_empty(self):self.assertEqual(evaluate([])['state'],'insufficient')
    def test_single(self):self.assertEqual(evaluate(series(100))['state'],'insufficient')
    def test_absolute(self):self.assertTrue(evaluate(series(100,100,700))['absolute_exceeded'])
    def test_relative(self):self.assertTrue(evaluate(series(100,100,200),threshold_ms=500)['relative_exceeded'])
    def test_normal(self):self.assertEqual(evaluate(series(100,110,120))['state'],'normal')
    def test_equal_limit(self):self.assertFalse(evaluate(series(100,100,500))['absolute_exceeded'])
    def test_no_relative_single_baseline(self):self.assertFalse(evaluate(series(100,200))['relative_exceeded'])
    def test_invalid_thresholds(self):
        for v in (0,-1,True,float('nan'),float('inf')):
            with self.subTest(v=v),self.assertRaises(ValueError):evaluate([],threshold_ms=v)
    def test_invalid_ratios(self):
        for v in (1,0,True,float('nan')):
            with self.subTest(v=v),self.assertRaises(ValueError):evaluate([],ratio=v)
    def test_invalid_durations(self):
        for v in (-1,True,float('nan'),'123'):
            with self.subTest(v=v),self.assertRaises(ValueError):evaluate(series(v))
    def test_dashboard(self):
        result=evaluate_dashboard({'series':{'Bastion principal':series(100,100,900)}})
        self.assertEqual(len(result),len(STEPS));self.assertEqual(result['Bastion principal']['state'],'degraded')
    def test_dashboard_invalid(self):
        with self.assertRaises(ValueError):evaluate_dashboard({})
    def test_gui_controls(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/'ssh_history_dashboard.py').read_text()
        self.assertIn('self.latency_limit',code);self.assertIn('self.alert_summary',code)
