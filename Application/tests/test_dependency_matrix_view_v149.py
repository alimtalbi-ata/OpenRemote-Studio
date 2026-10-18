import unittest
from dependency_matrix_view import eligible_connection_ids

class MatrixSelectionTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(eligible_connection_ids({'connection_ids':['a','b']},{'a','b'}),['a','b'])
    def test_stale(self):
        self.assertEqual(eligible_connection_ids({'connection_ids':['a','old']},{'a'}),['a'])
    def test_duplicates(self):
        self.assertEqual(eligible_connection_ids({'connection_ids':['a','a']},{'a'}),['a'])
    def test_empty(self):
        self.assertEqual(eligible_connection_ids({'connection_ids':[]},set()),[])
    def test_invalid_group(self):
        with self.assertRaises(ValueError):eligible_connection_ids(None,set())
    def test_invalid_ids(self):
        with self.assertRaises(ValueError):eligible_connection_ids({'connection_ids':'a'},set())
    def test_invalid_inventory(self):
        with self.assertRaises(ValueError):eligible_connection_ids({'connection_ids':[]},[])
    def test_non_string(self):
        self.assertEqual(eligible_connection_ids({'connection_ids':[None,4,'a']},{'a'}),['a'])
