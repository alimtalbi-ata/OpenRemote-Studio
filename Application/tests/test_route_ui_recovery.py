import ast,unittest
from pathlib import Path
class RouteUiRecoveryTests(unittest.TestCase):
 def test_ui_compiles(self):
  s=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  ast.parse(s)
 def test_quarantine_visible(self):
  s=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  self.assertIn('def show_invalid_routes(self):',s)
  self.assertIn("('Corriger routes PAM',self.show_invalid_routes)",s)
  self.assertIn('self._show_route_warning()',s)
 def test_editor_reads_quarantined(self):
  s=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  self.assertIn("old=self.routes.raw_for_edit(c['id'])",s)
 def test_unsafe_actions_guarded(self):
  s=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  self.assertIn("route=self._safe_route(c['id'])",s)
  self.assertIn('if route is None:return',s)
