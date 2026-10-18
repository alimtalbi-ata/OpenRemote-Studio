"""Regression: deleted connection must not consume a reconnect candidate."""
import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class DeletedTargetReconnectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree=ast.parse((ROOT/'qt_app.py').read_text(encoding='utf8'))
    def method(self,name):
        return next(node for node in ast.walk(self.tree) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name)
    def test_overview_target_before_candidate(self):
        src=ast.get_source_segment((ROOT/'qt_app.py').read_text(encoding='utf8'),self.method('reconnect_overview_session'))
        self.assertLess(src.index('target=next('),src.index('self.external_sessions.reconnect_candidate(identity,pid)'))
    def test_dialog_target_before_candidate(self):
        src=ast.get_source_segment((ROOT/'qt_app.py').read_text(encoding='utf8'),self.method('reconnect_row'))
        self.assertLess(src.index('connection=next('),src.index('self.external_sessions.reconnect_candidate(identity,pid)'))
    def test_overview_missing_target_is_blocking(self):
        src=ast.get_source_segment((ROOT/'qt_app.py').read_text(encoding='utf8'),self.method('reconnect_overview_session'))
        self.assertIn('if target is None:',src)
    def test_dialog_missing_target_is_blocking(self):
        src=ast.get_source_segment((ROOT/'qt_app.py').read_text(encoding='utf8'),self.method('reconnect_row'))
        self.assertIn('if connection is None:',src)
