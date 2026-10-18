import unittest
from pathlib import Path
from session_presentation import session_status_label,session_empty_message,can_reconnect

class SessionPresentationTests(unittest.TestCase):
    def test_running(self):self.assertEqual(session_status_label({'status':'running'}),'Active (processus local)')
    def test_success(self):self.assertIn('code 0',session_status_label({'status':'exited','exit_code':0}))
    def test_failed(self):self.assertIn('23',session_status_label({'status':'exited','exit_code':23}))
    def test_unknown(self):self.assertIn('inconnu',session_status_label({'status':'exited','exit_code':None}))
    def test_empty(self):self.assertIn('Aucun processus',session_empty_message(0))
    def test_filtered(self):self.assertIn('filtres',session_empty_message(3,'xyz'))
    def test_reconnect(self):
        self.assertTrue(can_reconnect({'status':'exited'}))
        self.assertFalse(can_reconnect({'status':'running'}))
        self.assertFalse(can_reconnect(None))
    def test_ui_wiring(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf8')
        self.assertIn('self.session_empty.setText(session_empty_message(',source)
        self.assertIn('self.session_reconnect_button.setEnabled(self._selected_session_reconnect_allowed())',source)
