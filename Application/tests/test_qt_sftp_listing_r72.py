"""Regression for Qt SFTP directory listing completion.

Static wiring test, not a live Windows GUI test.
Author: Abdelhalim Talbi.
"""
import ast
from pathlib import Path
import unittest


class QtSftpListingTests(unittest.TestCase):
    def test_refresh_captures_path_and_rejects_stale_result(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        refresh=next(n for n in ast.walk(tree)
                     if isinstance(n,ast.FunctionDef) and n.name=='refresh_remote'
                     and any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name)
                             and x.func.id=='queue_job' for x in ast.walk(n)))
        requested=next(n for n in refresh.body if isinstance(n,ast.Assign)
                       and any(isinstance(t,ast.Name) and t.id=='requested' for t in n.targets))
        self.assertIsInstance(requested.value,ast.Call)
        guard=next(n for n in refresh.body if isinstance(n,ast.FunctionDef)
                   and n.name=='show_if_current')
        self.assertIsInstance(guard.body[0],ast.If)
        self.assertIsInstance(guard.body[0].body[0],ast.Return)
        self.assertIsInstance(guard.body[0].test,ast.Compare)
        self.assertIsInstance(guard.body[0].test.ops[0],ast.NotEq)
        call=next(n for n in ast.walk(refresh) if isinstance(n,ast.Call)
                  and isinstance(n.func,ast.Name) and n.func.id=='queue_job')
        self.assertEqual(call.args[1].id,'requested')
        self.assertEqual(call.args[3].id,'show_if_current')


if __name__=='__main__':
    unittest.main()
