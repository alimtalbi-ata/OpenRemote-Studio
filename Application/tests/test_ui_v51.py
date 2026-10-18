import ast,unittest
from pathlib import Path
SOURCE=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
class ContextMenuTests(unittest.TestCase):
 def test_qt_syntax(self):ast.parse(SOURCE)
 def test_context_menu_installed(self):
  self.assertIn('self.tree.customContextMenuRequested.connect(self.connection_context_menu)',SOURCE)
 def test_context_menu_guards_group_rows(self):
  self.assertIn('if item is None or not item.data(0,Qt.UserRole):return',SOURCE)
 def test_search_uses_allowlist(self):
  self.assertIn("('name','host','group','protocol','tags','user')",SOURCE)
  self.assertNotIn("' '.join(str(value) for value in c.values())",SOURCE)
