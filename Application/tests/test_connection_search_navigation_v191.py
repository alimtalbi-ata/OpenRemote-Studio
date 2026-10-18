"""Regression tests for the Home -> Connections search navigation."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ConnectionSearchNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'qt_app.py').read_text(encoding='utf-8')
        cls.tree = ast.parse(cls.source)

    def test_only_one_search_navigation_method_per_class(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                names = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                self.assertLessEqual(names.count('focus_connection_search'), 1, node.name)

    def test_search_action_activates_connections_tab(self):
        method = next(node for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef) and node.name == 'focus_connection_search')
        body = ast.get_source_segment(self.source, method)
        self.assertIn('self.tabs.setCurrentWidget(self.home)', body)
        self.assertIn('self.search.setFocus()', body)
        self.assertIn('self.search.selectAll()', body)

    def test_home_shortcut_is_wired(self):
        home = (ROOT / 'home_workspace.py').read_text(encoding='utf-8')
        self.assertIn("'focus_connection_search'", home)
        self.assertIn('Rechercher un serveur', home)

    def test_search_does_not_reset_filters_or_connect(self):
        method = next(node for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef) and node.name == 'focus_connection_search')
        body = ast.get_source_segment(self.source, method)
        self.assertNotIn('reset_connection_filters(', body)
        self.assertNotIn('self.connect(', body)
