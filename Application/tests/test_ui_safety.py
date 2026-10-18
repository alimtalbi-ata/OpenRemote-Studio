
import ast
import unittest
from pathlib import Path
class UiSafetyTests(unittest.TestCase):
    def test_workers_are_isolated(self):
        root=Path(__file__).resolve().parents[1]
        worker=(root/'qt_workers.py').read_text()
        app=(root/'qt_app.py').read_text()
        self.assertIn('class SftpJob',worker)
        self.assertIn('from qt_workers import SftpJob, TcpJob',app)
        self.assertNotIn('class SftpJob',app)
    def test_dashboard_escapes_connection_names(self):
        app=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('escape(names[i])',app)
        self.assertIn('escape(str(k))',app)
    def test_home_tab_is_protected(self):
        app=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('if widget is self.home:',app)
    def test_ast_parses(self):
        root=Path(__file__).resolve().parents[1]
        for name in ['qt_app.py','qt_workers.py']:
            ast.parse((root/name).read_text(),filename=name)
