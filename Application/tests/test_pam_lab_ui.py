import ast,unittest
from pathlib import Path
class LabUiTests(unittest.TestCase):
 def test_menu_and_method(self):
  tree=ast.parse((Path(__file__).resolve().parents[1]/'qt_app.py').read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Main')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='show_pam_lab')
  source=ast.get_source_segment((Path(__file__).resolve().parents[1]/'qt_app.py').read_text(),method)
  self.assertIn('SimulatedPamBroker',source)
  self.assertNotIn('subprocess.Popen',source)
  self.assertNotIn('webbrowser.open',source)
  self.assertIn('approval.isChecked()',source)
  self.assertIn('consume.setEnabled(False)',source)
 def test_lab_not_wired_to_real_connect(self):
  tree=ast.parse((Path(__file__).resolve().parents[1]/'qt_app.py').read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Main')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='connect')
  self.assertNotIn('SimulatedPamBroker',ast.get_source_segment((Path(__file__).resolve().parents[1]/'qt_app.py').read_text(),method))
