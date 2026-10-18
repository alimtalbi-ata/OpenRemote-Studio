import unittest
from pathlib import Path
from session_presentation import selected_reconnect_allowed

ROWS=[{'connection_id':'a','pid':11,'status':'exited'}, {'connection_id':'a','pid':12,'status':'running'}, {'connection_id':'b','pid':21,'status':'exited'}]
class TestReconnectSelection(unittest.TestCase):
    def test_running_row_cannot_reconnect(self):self.assertFalse(selected_reconnect_allowed(ROWS,'a',12))
    def test_exited_with_active_sibling_blocked(self):self.assertFalse(selected_reconnect_allowed(ROWS,'a',11))
    def test_independent_exited_connection_allowed(self):self.assertTrue(selected_reconnect_allowed(ROWS,'b','21'))
    def test_unknown_pid_blocked(self):self.assertFalse(selected_reconnect_allowed(ROWS,'b',99))
    def test_no_selection_blocked(self):self.assertFalse(selected_reconnect_allowed(ROWS,None,None))
    def test_gui_uses_same_guard(self):
        src=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('reconnect.setEnabled(self._selected_session_reconnect_allowed())',src)
        self.assertIn('if not self._selected_session_reconnect_allowed():',src)
