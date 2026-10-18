import ast,unittest
from pathlib import Path
class V49Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  cls.tree=ast.parse(cls.source)
  cls.main=next(n for n in cls.tree.body if isinstance(n,ast.ClassDef) and n.name=='Main')
 def method(self,name):return next(n for n in self.main.body if isinstance(n,ast.FunctionDef) and n.name==name)
 def test_favorites_filter_present(self):
  self.assertIn("self.favorites_only.setCheckable(True)",self.source)
  self.assertIn("self.favorites_only.toggled.connect(self.refresh)",self.source)
 def test_favorites_filter_uses_workspace(self):
  self.assertIn("if self.favorites_only.isChecked() and c['id'] not in self.workspace.data['favorites']:continue",self.source)
 def test_duplicate_guard_at_common_launch(self):
  method=self.method('launch_connection')
  self.assertIsInstance(method.body[0],ast.If)
  self.assertIn('has_running',ast.unparse(method.body[0].test))
 def test_web_exempt_from_process_guard(self):
  self.assertIn("c['protocol']!='WEB' and self.external_sessions.has_running(c['id'])",self.source)
 def test_reconnect_reuses_guarded_launch(self):
  self.assertIn('self.launch_connection(c)',ast.unparse(self.method('reconnect_selected')))
