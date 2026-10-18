"""V10.7 source and scope contract tests without requiring a GUI runtime."""
import pathlib
import tempfile
import unittest
from ssh_route_scope import route_token
from ssh_diagnostic_history import DiagnosticHistory

ROOT=pathlib.Path(__file__).resolve().parents[1]

class ScopeUIV107Tests(unittest.TestCase):
    def test_editor_has_opt_in_fields(self):
        code=(ROOT/'qt_app.py').read_text()
        self.assertIn('self.ssh_scope_name=QLineEdit()',code)
        self.assertIn('self.ssh_scope_secret.setEchoMode(QLineEdit.Password)',code)
    def test_editor_clears_secret(self):
        self.assertIn('finally:self.ssh_scope_secret.clear()', (ROOT/'qt_app.py').read_text())
    def test_editor_passes_scope_on_save(self):
        self.assertIn('route_id=self._selected_route_token()', (ROOT/'qt_app.py').read_text())
    def test_dashboard_scoped_query(self):
        code=(ROOT/'ssh_history_dashboard.py').read_text()
        self.assertIn('route_id=self.route_id',code)
    def test_same_route_same_key(self):
        self.assertEqual(route_token('prod-hop',b'a'*32),route_token('prod-hop',b'a'*32))
    def test_different_keys(self):
        self.assertNotEqual(route_token('prod-hop',b'a'*32),route_token('prod-hop',b'b'*32))
    def test_short_secret_rejected(self):
        with self.assertRaises(ValueError):route_token('prod-hop',b'weak')
    def test_db_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            history=DiagnosticHistory(pathlib.Path(tmp)/'history.db')
            self.assertEqual(history.statistics(route_id=route_token('prod-hop',b'a'*32))['count'],0)
