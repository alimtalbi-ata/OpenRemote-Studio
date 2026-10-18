import ast
import unittest
from pathlib import Path

SRC=Path(__file__).resolve().parents[1]/'qt_app.py'
class TestUnifiedCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree=ast.parse(SRC.read_text(encoding='utf-8'))
        cls.code=SRC.read_text(encoding='utf-8')
    def test_method_present(self):
        self.assertTrue(any(isinstance(n,ast.FunctionDef) and n.name=='show_connection_card' for n in ast.walk(self.tree)))
    def test_actions_reuse_existing_probes(self):
        self.assertIn("('Tester TCP',self.test_tcp_connection)",self.code)
        self.assertIn("('Tester via bastion',self.test_ssh_jump_path)",self.code)
    def test_history_scoped(self):
        self.assertIn("self.probe_history.recent(c['id'],limit=50)",self.code)
    def test_context_menu(self):
        self.assertIn("('Fiche de connexion',self.show_connection_card)",self.code)
