import ast
import unittest
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/'qt_app.py'

class TestSshTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SOURCE.read_text(encoding='utf-8')
        cls.tree=ast.parse(cls.source)
        cls.method=next(n for n in cls.tree.body if isinstance(n,ast.ClassDef) and n.name=='SSHPathDialog')
        cls.init=next(n for n in cls.method.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        cls.text=ast.get_source_segment(cls.source,cls.init)
    def test_three_tabs(self):
        for label in ('Parcours','Diagnostic','Historique et audit'):
            self.assertIn("addTab(",self.text)
            self.assertIn("'"+label+"'",self.text)
    def test_save_cancel_always_visible(self):
        self.assertIn('outer.addWidget(actions)',self.text)
    def test_existing_handlers_retained(self):
        for method in ('test_local_hops','test_e2e_hops','export_signed_history','import_signed_history','show_import_audit'):
            self.assertIn('self.'+method,self.text)
    def test_no_network_on_tab_switch(self):
        self.assertNotIn('currentChanged.connect',self.text)
    def test_no_key_persistence(self):
        self.assertIn('setEchoMode(QLineEdit.Password)',self.text)
    def test_diagnostic_in_own_tab(self):
        self.assertLess(self.text.index("addTab(diagnostic_page"),self.text.index('self.diagnose=QPushButton'))
    def test_history_in_own_tab(self):
        self.assertLess(self.text.index("addTab(history_scroll"),self.text.index('self.ssh_scope_name=QLineEdit'))
