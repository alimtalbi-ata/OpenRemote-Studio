import unittest
from dependency_summary import summarize_trends

class TestSummary(unittest.TestCase):
    def setUp(self):
        self.report={'groups':[{'dependency_type':'SSH','connections':3,'previous_errors':1,'current_errors':4,'simultaneous_windows':2},
                               {'dependency_type':'RDP','connections':2,'previous_errors':3,'current_errors':0,'simultaneous_windows':0}]}
    def test_order(self):
        self.assertEqual(summarize_trends(self.report)[0]['dependency_type'],'SSH')
    def test_delta(self):
        self.assertEqual(summarize_trends(self.report)[0]['delta'],3)
    def test_affected(self):
        self.assertEqual(len(summarize_trends(self.report,affected_only=True)),1)
    def test_limit(self):
        self.assertEqual(len(summarize_trends(self.report,limit=1)),1)
    def test_invalid_limit(self):
        with self.assertRaises(ValueError): summarize_trends(self.report,limit=0)
    def test_invalid_report(self):
        with self.assertRaises(ValueError): summarize_trends(None)
    def test_negative_ignored(self):
        self.report['groups'][0]['current_errors']=-1
        self.assertEqual(len(summarize_trends(self.report)),1)
