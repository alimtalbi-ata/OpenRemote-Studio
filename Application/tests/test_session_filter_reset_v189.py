"""Regression checks for session workspace reset affordance."""
import unittest
from pathlib import Path
from session_view import filter_sessions

ROOT=Path(__file__).resolve().parents[1]
class SessionResetTests(unittest.TestCase):
    def test_ui_exposes_reset_button(self):
        source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn("setObjectName('resetSessionFilters')",source)
        self.assertIn('clicked.connect(self.reset_session_filters)',source)
    def test_reset_does_not_clear_registry(self):
        source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        body=source.split('    def reset_session_filters(self):',1)[1].split('    def _update_session_refresh',1)[0]
        self.assertIn('self.session_search.clear()',body)
        self.assertIn('self.session_state.setCurrentIndex(0)',body)
        self.assertNotIn('clear_exited',body)
        self.assertNotIn('history.delete',body)
    def test_reset_filter_restores_all_rows(self):
        rows=[{'name':'alpha','protocol':'ssh','pid':1,'connection_id':'a','status':'running'}, {'name':'beta','protocol':'rdp','pid':2,'connection_id':'b','status':'exited','exit_code':1}]
        self.assertEqual(len(filter_sessions(rows,'alpha','running')),1)
        self.assertEqual(filter_sessions(rows,'','all'),rows)
if __name__=='__main__':unittest.main()
