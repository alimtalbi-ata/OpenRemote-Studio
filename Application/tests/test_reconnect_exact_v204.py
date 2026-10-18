"""Regression: reconnect must use the exact selected process."""
import unittest
from pathlib import Path
from unittest.mock import Mock
from external_sessions import ExternalSessionRegistry

class TestReconnectExact(unittest.TestCase):
    def registry(self, rows):
        registry=ExternalSessionRegistry.__new__(ExternalSessionRegistry)
        registry.snapshot=Mock(return_value=rows)
        return registry
    def test_exact_selected_exited(self):
        rows=[dict(connection_id='a',pid=11,status='exited'),dict(connection_id='a',pid=12,status='exited')]
        self.assertIs(self.registry(rows).reconnect_candidate('a',11),rows[0])
    def test_missing_pid_rejected(self):
        self.assertIsNone(self.registry([dict(connection_id='a',pid=11,status='exited')]).reconnect_candidate('a'))
    def test_running_sibling_blocks(self):
        rows=[dict(connection_id='a',pid=11,status='exited'),dict(connection_id='a',pid=12,status='running')]
        self.assertIsNone(self.registry(rows).reconnect_candidate('a',11))
    def test_duplicate_identity_rejected(self):
        rows=[dict(connection_id='a',pid=11,status='exited'),dict(connection_id='a',pid='011',status='exited')]
        self.assertIsNone(self.registry(rows).reconnect_candidate('a',11))
    def test_unknown_or_active_pid_rejected(self):
        rows=[dict(connection_id='a',pid=11,status='running')]
        self.assertIsNone(self.registry(rows).reconnect_candidate('a',11))
        self.assertIsNone(self.registry(rows).reconnect_candidate('a',99))
    def test_gui_passes_selected_pid(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('self.external_sessions.reconnect_candidate(identity,pid)',source)

if __name__=='__main__':unittest.main()
