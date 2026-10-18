
import ast
import unittest
from pathlib import Path
class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
    def test_syntax(self): ast.parse(self.code)
    def test_primary_toolbar_reduced(self):
        self.assertIn("('＋ Nouvelle connexion',None,self.add",self.code)
        self.assertIn("('Transfert SFTP','sftp',self.sftp",self.code)
        self.assertIn("self.menuBar().addMenu('Sécurité')",self.code)
    def test_home_guard_precedes_process_shutdown(self):
        close=self.code.split('    def close_tab(self,index):',1)[1].split('    def show_integrations',1)[0]
        self.assertLess(close.index('if widget is self.home:'),close.index('for proc in list(self.processes):'))
    def test_toolbox_no_duplicate_item(self):
        self.assertEqual(self.code.count("item=QListWidgetItem(f'{category}  /  {name}')"),1)
