"""Regression checks for the external sessions dialog. Author: Abdelhalim Talbi."""
import unittest
from pathlib import Path
from session_reconnect_choices import reconnect_choice_still_valid

SOURCE = (Path(__file__).resolve().parents[1] / 'qt_app.py').read_text(encoding='utf-8')

class ExternalDialogReconnectTests(unittest.TestCase):
    def test_dialog_stores_pid(self):
        self.assertIn("row.setData(0,Qt.UserRole+1,item['pid'])", SOURCE)
    def test_dialog_reads_pid(self):
        self.assertIn("pid=row.data(0,Qt.UserRole+1)", SOURCE)
    def test_dialog_checks_fresh_snapshot(self):
        self.assertIn("reconnect_choice_still_valid(self.external_sessions.snapshot(), identity, pid)", SOURCE)
    def test_exact_exited_session(self):
        self.assertTrue(reconnect_choice_still_valid([{'connection_id':'a','pid':42,'status':'exited'}], 'a',42))
    def test_active_sibling_blocks(self):
        rows=[{'connection_id':'a','pid':42,'status':'exited'}, {'connection_id':'a','pid':43,'status':'running'}]
        self.assertFalse(reconnect_choice_still_valid(rows,'a',42))
    def test_ambiguous_identity_blocks(self):
        rows=[{'connection_id':'a','pid':42,'status':'exited'}, {'connection_id':'a','pid':'042','status':'exited'}]
        self.assertFalse(reconnect_choice_still_valid(rows,'a',42))
    def test_stale_pid_blocks(self):
        self.assertFalse(reconnect_choice_still_valid([{'connection_id':'a','pid':43,'status':'exited'}], 'a',42))

if __name__=='__main__': unittest.main()
