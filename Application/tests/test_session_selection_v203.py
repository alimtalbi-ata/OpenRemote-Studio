import unittest
from session_selection import session_identity, selected_session, preserved_session_identity

class SessionSelectionV203Tests(unittest.TestCase):
    def test_leading_zero_pid_canonicalized(self):
        self.assertEqual(session_identity({'connection_id':'c','pid':'00042'}), ('c','42'))
    def test_exact_lookup_accepts_canonical_equivalence(self):
        row={'connection_id':'c','pid':'00042'}
        self.assertIs(selected_session([row], 'c', 42), row)
    def test_duplicate_identity_is_ambiguous(self):
        rows=[{'connection_id':'c','pid':'42'}, {'connection_id':'c','pid':'042'}]
        self.assertIsNone(selected_session(rows,'c',42))
    def test_ambiguous_selection_not_preserved(self):
        rows=[{'connection_id':'c','pid':42}, {'connection_id':'c','pid':42}]
        self.assertIsNone(preserved_session_identity(rows, ('c','42')))
    def test_unique_selection_preserved_canonically(self):
        self.assertEqual(preserved_session_identity([{'connection_id':'c','pid':42}], ('c','00042')), ('c','42'))
    def test_invalid_row_not_selected(self):
        self.assertIsNone(selected_session([{'connection_id':'c','pid':0}], 'c', 0))
