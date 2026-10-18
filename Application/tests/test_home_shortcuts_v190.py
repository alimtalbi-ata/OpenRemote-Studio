import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class HomeShortcutsV190Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home=(ROOT/'home_workspace.py').read_text(encoding='utf8')
        cls.ui=(ROOT/'qt_app.py').read_text(encoding='utf8')
    def test_search_shortcut(self): self.assertIn("'focus_connection_search'",self.home)
    def test_history_shortcut(self): self.assertIn("'show_session_history'",self.home)
    def test_incidents_shortcut(self): self.assertIn("'show_incident_overview'",self.home)
    def test_search_focus(self): self.assertIn('self.search.setFocus()',self.ui)
    def test_search_preserves_filters(self): self.assertIn('self.search.selectAll()',self.ui)
    def test_no_automatic_network(self):
        self.assertNotIn('subprocess',self.home)
        self.assertNotIn('socket',self.home)
    def test_accessibility(self): self.assertIn("button.setObjectName('homeShortcut_' + key)",self.home)
