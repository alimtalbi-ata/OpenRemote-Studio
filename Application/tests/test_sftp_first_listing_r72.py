"""Source-level regression for SFTP UI task completion ordering.

Not a live GUI test. Author: Abdelhalim Talbi.
"""
import ast
import unittest
from pathlib import Path


class SFTPFirstListingTests(unittest.TestCase):
    def test_successful_connect_triggers_listing_after_busy_release(self):
        source = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
        module = ast.parse(source)
        app = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'App')
        browser = next(n for n in app.body if isinstance(n, ast.FunctionDef) and n.name == 'sftp_browser')
        task = next(n for n in browser.body if isinstance(n, ast.FunctionDef) and n.name == 'task')
        complete = next(n for n in ast.walk(task) if isinstance(n, ast.FunctionDef) and n.name == 'complete')
        self.assertIsInstance(complete.body[0], ast.Assign)
        self.assertEqual(complete.body[0].targets[0].slice.value, 'busy')
        self.assertIs(complete.body[0].value.value, False)
        self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                            and n.func.id == 'on_success' for n in ast.walk(complete)))
        calls = [n for n in ast.walk(browser) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'task']
        self.assertTrue(any(any(k.arg == 'on_success' and isinstance(k.value, ast.Name)
                                 and k.value.id == 'refresh' for k in call.keywords)
                            for call in calls))


if __name__ == '__main__':
    unittest.main()
