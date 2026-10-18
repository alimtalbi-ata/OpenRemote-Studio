import ast,unittest
from pathlib import Path
class UiV50Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  cls.main=next(x for x in ast.parse(cls.source).body if isinstance(x,ast.ClassDef) and x.name=='Main')
 def method(self,name):
  return next(x for x in self.main.body if isinstance(x,ast.FunctionDef) and x.name==name)
 def test_shortcut_setup(self):
  self.assertIn('self._install_shortcuts()',self.source)
  self.assertIn("('Ctrl+F', 'focus_connection_search')",(Path(__file__).resolve().parents[1]/'workspace_shortcuts.py').read_text().replace('\"',"'"))
 def test_tab_navigation(self):
  self.method('next_tab');self.method('previous_tab');self.method('close_current_tab')
 def test_session_overview_tab(self):
  self.method('show_session_overview');self.method('refresh_session_overview')
  self.assertIn("self.tabs.addTab(pane,'Sessions')",self.source)
 def test_external_clients_not_embedded(self):
  self.assertIn('Son PID ne prouve pas',self.source)
 def test_session_overview_refresh_after_launch(self):
  self.assertIn('self.refresh_session_overview()',ast.unparse(self.method('launch_connection')))
 def test_no_close_home(self):
  self.assertIn('if widget is self.home:',ast.unparse(self.method('close_tab')))
