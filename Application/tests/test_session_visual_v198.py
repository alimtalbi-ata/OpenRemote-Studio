import unittest
from session_presentation import session_visual_state

class SessionVisualTests(unittest.TestCase):
    def test_running_does_not_claim_remote_health(self):
        state, help_text = session_visual_state({'status':'running'})
        self.assertEqual(state,'running')
        self.assertIn('non vérifiée',help_text)
    def test_exit_success(self):
        self.assertEqual(session_visual_state({'status':'exited','exit_code':0})[0],'completed')
    def test_exit_failure(self):
        state, help_text=session_visual_state({'status':'exited','exit_code':255})
        self.assertEqual(state,'failed')
        self.assertIn('255',help_text)
    def test_unknown_exit(self):
        self.assertEqual(session_visual_state({'status':'exited','exit_code':None})[0],'unknown')
    def test_unknown_status(self):
        self.assertEqual(session_visual_state({'status':'weird'})[0],'unknown')
    def test_gui_wiring(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('session_visual_state(item)',source)
        self.assertIn('entry.setToolTip(3, explanation)',source)
