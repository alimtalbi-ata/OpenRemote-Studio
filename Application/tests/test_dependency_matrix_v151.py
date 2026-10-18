import unittest
from dependency_matrix_filters import incident_priority,visible_group_indices

class MatrixV151Tests(unittest.TestCase):
    def test_priorities(self):
        self.assertEqual(incident_priority({'overlap_windows':2,'max_simultaneous_connections':3,'affected_connections':3}),'forte')
        self.assertEqual(incident_priority({'overlap_windows':1,'max_simultaneous_connections':2,'affected_connections':2}),'moderee')
        self.assertEqual(incident_priority({'affected_connections':1}),'a_examiner')
        self.assertEqual(incident_priority({}),'sans_echec')
    def test_invalid_counter(self):
        for value in (-1,True,'3'):
            with self.assertRaises(ValueError):incident_priority({'affected_connections':value})
    def test_filter(self):
        groups=[{}, {'affected_connections':1}, {'overlap_windows':1,'max_simultaneous_connections':2,'affected_connections':2}]
        self.assertEqual(visible_group_indices(groups),[0,1,2])
        self.assertEqual(visible_group_indices(groups,'AFFECTED'),[1,2])
        self.assertEqual(visible_group_indices(groups,'SIMULTANEOUS'),[2])
    def test_bad_filter(self):
        with self.assertRaises(ValueError):visible_group_indices([],'BAD')
    def test_invalid_group_skipped(self):
        self.assertEqual(visible_group_indices([None,{}]),[1])
