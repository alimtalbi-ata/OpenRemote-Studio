"""Regression: initial SFTP listing must not be discarded as busy.

This is a source-level wiring test, not a live Windows GUI qualification.
Author: Abdelhalim Talbi.
"""
import ast
import unittest
from pathlib import Path


class SFTPFirstListingTests(unittest.TestCase):
    def test_first_listing_releases_busy_before_refresh(self):
        source = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
        module = ast.parse(source)
        app = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'App')
        browser = next(node for node in app.body if isinstance(node, ast.FunctionDef) and node.name == 'sftp_browser')
        initial = next(node for node in ast.walk(browser)
                       if isinstance(node, ast.FunctionDef) and node.name == 'first_refresh')
        self.assertGreaterEqual(len(initial.body), 2)
        first, second = initial.body[:2]
        self.assertIsInstance(first, ast.Assign)
        self.assertIsInstance(first.targets[0], ast.Subscript)
        self.assertEqual(first.targets[0].slice.value, 'busy')
        self.assertIsInstance(first.value, ast.Constant)
        self.assertIs(first.value.value, False)
        self.assertIsInstance(second, ast.Expr)
        self.assertIsInstance(second.value, ast.Call)
        self.assertEqual(second.value.func.id, 'refresh')


if __name__ == '__main__':
    unittest.main()
