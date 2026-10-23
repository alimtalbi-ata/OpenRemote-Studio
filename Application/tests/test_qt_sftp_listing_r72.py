"""Regression for Qt SFTP directory labels during asynchronous listing.

Static wiring test; live Windows GUI qualification remains required.
Author: Abdelhalim Talbi.
"""
import ast
from pathlib import Path
import unittest


class QtSftpListingTests(unittest.TestCase):
    def test_refresh_captures_requested_path(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        methods=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='refresh_remote']
        self.assertTrue(methods)
        refresh=next(n for n in methods if any(
            isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='queue_job'
            for x in ast.walk(n)))
        assignments=[n for n in refresh.body if isinstance(n,ast.Assign)]
        self.assertTrue(any(any(isinstance(t,ast.Name) and t.id=='requested' for t in n.targets)
                            for n in assignments))
        call=next(n for n in ast.walk(refresh) if isinstance(n,ast.Call)
                  and isinstance(n.func,ast.Name) and n.func.id=='queue_job')
        self.assertIsInstance(call.args[1],ast.Name)
        self.assertEqual(call.args[1].id,'requested')


if __name__=='__main__':
    unittest.main()
