import unittest
from pathlib import Path
from workspace_navigation import primary_views, resolve_view
ROOT=Path(__file__).resolve().parents[1]
class NavigationTests(unittest.TestCase):
    def test_three_views(self): self.assertEqual(len(primary_views()),3)
    def test_labels_unique(self): self.assertEqual(len({x[0] for x in primary_views()}),3)
    def test_shortcuts_unique(self): self.assertEqual(len({x[2] for x in primary_views()}),3)
    def test_resolve_sessions(self): self.assertEqual(resolve_view('Sessions'),'show_session_overview')
    def test_invalid_fails_closed(self):
        with self.assertRaises(ValueError): resolve_view('Unknown')
    def test_ui_buttons(self): self.assertIn('primaryNavigation', (ROOT/'qt_app.py').read_text())
    def test_shortcuts(self):
        source=(ROOT/'qt_app.py').read_text()
        self.assertIn("('Ctrl+2', 'show_session_overview')",(Path(__file__).resolve().parents[1]/'workspace_shortcuts.py').read_text().replace('\"',"'"))
        self.assertIn("('Ctrl+3', 'show_local_readiness')",(Path(__file__).resolve().parents[1]/'workspace_shortcuts.py').read_text().replace('\"',"'"))
if __name__=='__main__': unittest.main()
