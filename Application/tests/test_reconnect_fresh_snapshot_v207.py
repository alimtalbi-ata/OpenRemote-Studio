import unittest
from session_reconnect_choices import reconnect_choice_still_valid

class FreshReconnectTests(unittest.TestCase):
    def row(self,pid,status='exited',cid='server'):
        return {'connection_id':cid,'pid':pid,'status':status,'exit_code':0}
    def test_exact_exited(self):
        self.assertTrue(reconnect_choice_still_valid([self.row(42)],'server',42))
    def test_running_sibling(self):
        self.assertFalse(reconnect_choice_still_valid([self.row(42),self.row(43,'running')],'server',42))
    def test_duplicate_identity(self):
        self.assertFalse(reconnect_choice_still_valid([self.row(42),self.row('042')],'server',42))
    def test_missing(self):
        self.assertFalse(reconnect_choice_still_valid([self.row(43)],'server',42))
    def test_invalid(self):
        self.assertFalse(reconnect_choice_still_valid([self.row(42)],'server',True))
    def test_other_connection(self):
        self.assertFalse(reconnect_choice_still_valid([self.row(42)],'other',42))
