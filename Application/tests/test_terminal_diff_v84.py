import unittest
from terminal_diff import changed_rows

class TerminalDiffTests(unittest.TestCase):
    def test_first_frame(self):self.assertIsNone(changed_rows(None,('a',)))
    def test_no_changes(self):self.assertEqual(changed_rows(('a','b'),('a','b')),[])
    def test_single_change(self):self.assertEqual(changed_rows(('a','b','c','d'),('a','x','c','d')),[1])
    def test_shape_change(self):self.assertIsNone(changed_rows(('a',),('a','b')))
    def test_many_changes(self):self.assertIsNone(changed_rows(('a',)*8,('b',)*8))
    def test_explicit_limit(self):self.assertIsNone(changed_rows(('a',)*8,('b','b','a','a','a','a','a','a'),max_changes=1))
    def test_bad_limit(self):
        with self.assertRaises(ValueError):changed_rows((),(),max_changes=0)
