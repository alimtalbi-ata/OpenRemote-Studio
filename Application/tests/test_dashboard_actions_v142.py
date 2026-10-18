import unittest
from dashboard_actions import allowed_action,ACTIONS

class DashboardActionTests(unittest.TestCase):
    def test_all_actions(self):
        for action in ACTIONS:
            self.assertTrue(allowed_action(action,'a',['a','b']))
    def test_unknown_action(self):
        self.assertFalse(allowed_action('delete','a',['a']))
    def test_stale_connection(self):
        self.assertFalse(allowed_action('open','removed',['a']))
    def test_missing_selection(self):
        self.assertFalse(allowed_action('open','',['a']))
    def test_invalid_collection(self):
        self.assertFalse(allowed_action('open','a',None))
    def test_invalid_action(self):
        self.assertFalse(allowed_action(None,'a',['a']))
    def test_empty_inventory(self):
        self.assertFalse(allowed_action('tcp','a',[]))
