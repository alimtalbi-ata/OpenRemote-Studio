import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class ActiveNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
    def test_checkable_buttons(self): self.assertIn('button.setCheckable(True)',self.source)
    def test_accessibility(self): self.assertIn("button.setAccessibleName('Navigation '+title)",self.source)
    def test_tab_change_sync(self): self.assertIn('self.tabs.currentChanged.connect(self._sync_primary_navigation)',self.source)
    def test_home_sync(self): self.assertIn('self.home=home;self._sync_primary_navigation()',self.source)
    def test_no_network_side_effect(self):
        body=self.source.split('    def _sync_primary_navigation(',1)[1].split('    def show_home(',1)[0]
        self.assertNotIn('subprocess',body)
        self.assertNotIn('launch_connection(',body)
    def test_all_views_mapped(self):
        body=self.source.split('    def _sync_primary_navigation(',1)[1].split('    def show_home(',1)[0]
        for method in ('show_home','show_session_overview','show_local_readiness'): self.assertIn(method,body)
