import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "qt_app.py").read_text(encoding="utf-8")

class SessionRowIdentityTests(unittest.TestCase):
    def test_row_tracks_process_pid(self):
        self.assertIn("entry.setData(0,Qt.UserRole+1,str(item['pid']))", SOURCE)
    def test_detail_targets_exact_process(self):
        self.assertIn("row=selected_session(self.external_sessions.snapshot(), identity, pid)", SOURCE)
    def test_selection_restores_exact_row(self):
        self.assertIn("session_identity(item)==preserved", SOURCE)
    def test_no_latest_process_fallback(self):
        self.assertNotIn("row=rows[-1]", SOURCE)
