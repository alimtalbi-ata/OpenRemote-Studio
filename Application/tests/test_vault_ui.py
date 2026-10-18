
import ast
import unittest
from pathlib import Path
class VaultUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        cls.tree=ast.parse(cls.code)
    def test_locking_and_timeout(self):
        self.assertIn('self.vault_timer.setSingleShot(True)',self.code)
        self.assertIn('self.vault_timer.timeout.connect(self.lock_vault)',self.code)
        self.assertIn('self.vault_data.clear()',self.code)
    def test_secret_saved_before_memory_mutation(self):
        method=next(n for c in self.tree.body if isinstance(c,ast.ClassDef) and c.name=='Main' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='edit_secret')
        text=ast.get_source_segment(self.code,method)
        self.assertLess(text.index('self.vault.save(updated'),text.index('self.vault_data=updated'))
    def test_close_locks(self):
        self.assertIn('def closeEvent(self,event):',self.code)
        self.assertIn('super().closeEvent(event)',self.code)
