"""Reconnect must fail closed on malformed session snapshots."""
import unittest
from session_presentation import selected_reconnect_allowed


class SessionReconnectSafetyTests(unittest.TestCase):
    def test_malformed_sibling_blocks_reconnect(self):
        rows = [
            {"connection_id": "c1", "pid": 101, "status": "exited"},
            None,
        ]
        self.assertFalse(selected_reconnect_allowed(rows, "c1", 101))

    def test_running_sibling_blocks_reconnect(self):
        rows = [
            {"connection_id": "c1", "pid": 101, "status": "exited"},
            {"connection_id": "c1", "pid": 102, "status": "running"},
        ]
        self.assertFalse(selected_reconnect_allowed(rows, "c1", 101))

    def test_single_exited_session_allows_reconnect(self):
        rows = [{"connection_id": "c1", "pid": 101, "status": "exited"}]
        self.assertTrue(selected_reconnect_allowed(rows, "c1", 101))

    def test_other_connection_running_does_not_block(self):
        rows = [
            {"connection_id": "c1", "pid": 101, "status": "exited"},
            {"connection_id": "c2", "pid": 102, "status": "running"},
        ]
        self.assertTrue(selected_reconnect_allowed(rows, "c1", 101))


if __name__ == "__main__":
    unittest.main()
