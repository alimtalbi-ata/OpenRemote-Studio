"""Static integration checks for the V22.6 session inspection entry points."""
import unittest
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1].joinpath('qt_app.py').read_text(encoding='utf-8')
class SessionDetailsIntegration(unittest.TestCase):
 def test_double_click_is_wired(self):self.assertIn('itemDoubleClicked.connect(self.inspect_selected_session)',SOURCE)
 def test_details_button_is_wired(self):self.assertIn('details.clicked.connect(self.inspect_selected_session)',SOURCE)
 def test_details_button_initially_disabled(self):self.assertIn('self.session_details_button=details;details.setEnabled(False)',SOURCE)
 def test_details_button_tracks_selection(self):self.assertIn('self.session_details_button.setEnabled(self.session_overview_list.currentItem() is not None)',SOURCE)
 def test_inspection_rechecks_selected_identity(self):
  method=SOURCE.split('    def inspect_selected_session(self,*_):',1)[1].split('    def _selected_session_reconnect_allowed',1)[0]
  self.assertIn('selected_session(self.external_sessions.snapshot(),identity,pid)',method)
  self.assertNotIn('launch_connection(',method)
  self.assertNotIn('reconnect_candidate(',method)
 def test_details_are_read_only(self):
  method=SOURCE.split('    def inspect_selected_session(self,*_):',1)[1].split('    def _selected_session_reconnect_allowed',1)[0]
  self.assertIn('session_process_details(row)',method)
if __name__=='__main__':unittest.main()
