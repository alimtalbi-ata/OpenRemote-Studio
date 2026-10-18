"""Selection retention regression tests for the Windows connection browser."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SelectionRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.source=(ROOT/'qt_app.py').read_text(encoding='utf8')
    def test_selection_id_helper(self): self.assertIn('def selected_connection_id(self):',self.source)
    def test_selection_saved_before_tree_clear(self):
        body=self.source.split('    def refresh(self):',1)[1].split('    def connection_context_menu(',1)[0]
        self.assertLess(body.index('selected_id = self.selected_connection_id()'),body.index('self.tree.clear()'))
    def test_selection_restored_by_id(self): self.assertIn("if c['id'] == selected_id:",self.source)
    def test_no_network_in_selection_helper(self):
        body=self.source.split('    def selected_connection_id(self):',1)[1].split('    def selected(self):',1)[0]
        self.assertNotIn('subprocess',body)
    def test_selected_uses_shared_helper(self): self.assertIn('id=self.selected_connection_id()',self.source)
