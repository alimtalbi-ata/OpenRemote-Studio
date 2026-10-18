import ast,unittest
from pathlib import Path
class SessionRefreshTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
 def test_valid_python(self):ast.parse(self.source)
 def test_timer_interval(self):self.assertIn('self.session_refresh_timer.setInterval(3000)',self.source)
 def test_timer_lifecycle(self):
  self.assertIn('self.tabs.currentChanged.connect(self._update_session_refresh)',self.source)
  self.assertIn('self.session_refresh_timer.stop()',self.source)
 def test_context_menu(self):
  self.assertIn('def session_overview_context_menu(self,position):',self.source)
  self.assertIn("menu.addAction('Afficher détails du processus')",self.source)
 def test_reconnect_uses_secure_path(self):
  self.assertIn('if choice is reconnect:self.reconnect_overview_session()',self.source)
