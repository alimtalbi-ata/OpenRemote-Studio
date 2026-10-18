"""Regression checks for refreshing the existing diagnostic tab."""
import unittest
from pathlib import Path

class LocalDiagnosticRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = (Path(__file__).resolve().parents[1] / 'qt_app.py').read_text(encoding='utf-8')

    def test_existing_tab_reloads(self):
        self.assertIn('self.tabs.widget(index).reload_local_clients()', self.code)

    def test_reload_callback_is_bound(self):
        self.assertIn('pane.reload_local_clients = reload', self.code)

    def test_no_implicit_network_check(self):
        self.assertIn('report = inspect_clients()', self.code)
        self.assertIn('network', (Path(__file__).resolve().parents[1] / 'local_diagnostic_summary.py').read_text(encoding='utf-8'))

    def test_explicit_refresh_retained(self):
        self.assertIn("refresh.clicked.connect(reload)", self.code)
