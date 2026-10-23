"""Qt SFTP should initially list the authenticated user's working directory.

Static source regression only; live Windows validation is still required.
Author: Abdelhalim Talbi.
"""
import ast
from pathlib import Path
import unittest


class QtSftpHomeTests(unittest.TestCase):
    def test_initial_directory_is_dot(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8'))
        method=next(node for node in ast.walk(tree)
                    if isinstance(node,ast.FunctionDef) and node.name=='sftp')
        initial=[node for node in ast.walk(method)
                 if isinstance(node,ast.Assign)
                 and any(isinstance(t,ast.Name) and t.id=='path' for t in node.targets)
                 and isinstance(node.value,ast.Call)
                 and isinstance(node.value.func,ast.Name)
                 and node.value.func.id=='QLineEdit']
        self.assertEqual(len(initial),1)
        self.assertEqual(initial[0].value.args[0].value,'.')


if __name__=='__main__':
    unittest.main()
