import unittest
from dependency_summary import summarize_trends,resolve_group_connections

class TestSummaryNavigation(unittest.TestCase):
    def test_identities_preserved(self):
        report={'groups':[{'dependency_type':'SSH','current_errors':3,'previous_errors':1,'simultaneous_windows':1,'connections':2,'connection_ids':['b','a']}] }
        rows=summarize_trends(report)
        self.assertEqual(rows[0]['connection_ids'],('b','a'))
        self.assertEqual(resolve_group_connections(rows[0],{'a','b','c'}),['a','b'])
    def test_deleted_connection_ignored(self):
        self.assertEqual(resolve_group_connections({'connection_ids':['a','missing','a']},{'a'}),['a'])
    def test_malformed_row(self):
        self.assertEqual(resolve_group_connections({'connection_ids':'bad'},{'a'}),[])
    def test_invalid_input(self):
        with self.assertRaises(ValueError):resolve_group_connections(None,{'a'})
        with self.assertRaises(ValueError):resolve_group_connections({},['a'])
    def test_empty(self):
        self.assertEqual(resolve_group_connections({},set()),[])
