import unittest
from datetime import datetime, timezone
from dependency_trends import compare_dependency_trends

class TrendTests(unittest.TestCase):
    def test_empty(self):
        result=compare_dependency_trends([],{}, {'rows':[]},[],[],now=datetime(2026,10,16,tzinfo=timezone.utc))
        self.assertEqual(result['groups'],[])
        self.assertFalse(result['remote_cause_confirmed'])
    def test_invalid_periods(self):
        for value in (0,721,True,'30'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                compare_dependency_trends([],{}, {'rows':[]},[],[],minutes=value)
    def test_invalid_tolerance(self):
        with self.assertRaises(ValueError):
            compare_dependency_trends([],{}, {'rows':[]},[],[],tolerance_seconds=-1)
    def test_naive_time(self):
        with self.assertRaises(ValueError):
            compare_dependency_trends([],{}, {'rows':[]},[],[],now=datetime(2026,10,16))
    def test_utc_time(self):
        result=compare_dependency_trends([],{}, {'rows':[]},[],[],now=datetime(2026,10,16,tzinfo=timezone.utc))
        self.assertEqual(result['scope'],'local_only')
        self.assertEqual(result['minutes_per_period'],30)
