import unittest
from pathlib import Path
from workspace_shortcuts import workspace_shortcuts,validate_shortcuts
ROOT=Path(__file__).resolve().parents[1]
class WorkspaceShortcutsTests(unittest.TestCase):
    def test_unique_shortcuts(self): self.assertTrue(validate_shortcuts())
    def test_search_clear(self): self.assertIn(("Ctrl+Shift+F","clear_and_focus_connection_search"),workspace_shortcuts())
    def test_favorites_toggle(self): self.assertIn(("Ctrl+E","toggle_favorites_filter"),workspace_shortcuts())
    def test_existing_navigation(self):
        for key,handler in (("Ctrl+1","show_home"),("Ctrl+2","show_session_overview"),("Ctrl+3","show_local_readiness")):
            self.assertIn((key,handler),workspace_shortcuts())
    def test_methods_exist(self):
        source=(ROOT/'qt_app.py').read_text(encoding='utf8')
        for _,method in workspace_shortcuts(): self.assertIn('def '+method+'(',source)
    def test_no_remote_side_effects_in_toggle(self):
        source=(ROOT/'qt_app.py').read_text(encoding='utf8')
        body=source.split('    def toggle_favorites_filter(',1)[1].split('    def close_current_tab(',1)[0]
        self.assertNotIn('subprocess',body)
        self.assertNotIn('launch_connection',body)
