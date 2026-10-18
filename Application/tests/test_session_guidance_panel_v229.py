import unittest
from pathlib import Path
class TestPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
    def test_readonly(self):
        self.assertIn('self.session_guidance_panel.setReadOnly(True)',self.source)
    def test_identity_guard(self):
        block=self.source.split('    def refresh_guidance_panel(self):',1)[1].split('    def show_selected_session_guidance',1)[0]
        self.assertIn('selected_session(self.external_sessions.snapshot()',block)
        self.assertIn('row is None',block)
        self.assertNotIn('reconnect_overview_session(',block)
    def test_selection_refresh(self):
        self.assertIn('itemSelectionChanged.connect(self.refresh_guidance_panel)',self.source)
if __name__=='__main__':unittest.main()
