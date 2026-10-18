import unittest
from pathlib import Path
from session_presentation import session_visibility_summary,session_process_details

ROOT=Path(__file__).resolve().parents[1]
class SessionVisibilityV200(unittest.TestCase):
    def test_all(self):self.assertIn('3 processus',session_visibility_summary(3,3))
    def test_filtered(self):self.assertIn('1 processus',session_visibility_summary(3,1))
    def test_empty(self):self.assertIn('0 processus',session_visibility_summary(0,0))
    def test_bad_count(self):
        with self.assertRaises(ValueError):session_visibility_summary(1,2)
    def test_control_character_redaction(self):
        text=session_process_details({'name':'host\x1b[31m\t\u202e', 'protocol':'SSH'})
        self.assertNotIn('\x1b',text)
        self.assertNotIn('\u202e',text)
        self.assertNotIn('\t',text)
    def test_ui_integration(self):
        s=(ROOT/'qt_app.py').read_text()
        self.assertIn('sessionVisibleSummary',s)
        self.assertIn('session_visibility_summary(len(rows),len(visible))',s)
