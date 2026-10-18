import unittest
from dependency_matrix_view import group_at_index

class MatrixV150Tests(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(group_at_index([{'id':'a'},{'id':'b'}],1),{'id':'b'})
    def test_negative(self):
        self.assertIsNone(group_at_index([{'id':'a'}],-1))
    def test_stale(self):
        self.assertIsNone(group_at_index([{'id':'a'}],1))
    def test_missing(self):
        self.assertIsNone(group_at_index([{'id':'a'}],None))
    def test_boolean(self):
        self.assertIsNone(group_at_index([{'id':'a'}],True))
    def test_non_dict(self):
        self.assertIsNone(group_at_index(['a'],0))
    def test_invalid_collection(self):
        self.assertIsNone(group_at_index(None,0))
