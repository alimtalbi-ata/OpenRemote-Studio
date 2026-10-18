import unittest
from session_selection import session_identity, selected_session, preserved_session_identity
from session_presentation import selected_reconnect_allowed

class SessionSelectionV201Tests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'connection_id':'a','pid':12,'status':'exited'}, {'connection_id':'a','pid':13,'status':'running'}, {'connection_id':'b','pid':12,'status':'exited'}]
    def test_exact_process(self):
        self.assertIs(selected_session(self.rows,'a','13'),self.rows[1])
    def test_cross_connection(self):
        self.assertIs(selected_session(self.rows,'b',12),self.rows[2])
    def test_missing(self):
        self.assertIsNone(selected_session(self.rows,'a',99))
    def test_invalid_identity(self):
        self.assertIsNone(session_identity({'connection_id':'a','pid':'-1'}))
    def test_boolean_pid_rejected(self):
        self.assertIsNone(session_identity({'connection_id':'a','pid':True}))
    def test_selection_survives_filter(self):
        self.assertEqual(preserved_session_identity(self.rows[:2],('a','13')),('a','13'))
    def test_selection_cleared_when_filtered(self):
        self.assertIsNone(preserved_session_identity(self.rows[:1],('a','13')))
    def test_reconnect_refuses_active_sibling(self):
        self.assertFalse(selected_reconnect_allowed(self.rows,'a',12))
    def test_reconnect_other_connection(self):
        self.assertTrue(selected_reconnect_allowed(self.rows,'b',12))
    def test_malformed_rows(self):
        self.assertIsNone(selected_session([None, {}, 1], 'a',12))

if __name__=='__main__':unittest.main()
