"""Regression tests for exact session identity and fail-closed selection."""
import unittest

from session_selection import (
    preserved_session_identity,
    selected_session,
    session_identity,
)


class SessionSelectionTests(unittest.TestCase):
    def test_pid_is_canonicalized_without_collapsing_distinct_connections(self):
        self.assertEqual(session_identity({"connection_id": "srv-1", "pid": "0012"}), ("srv-1", "12"))
        self.assertIsNone(session_identity({"connection_id": " ", "pid": 12}))
        self.assertIsNone(session_identity({"connection_id": "srv-1", "pid": True}))
        self.assertIsNone(session_identity({"connection_id": "srv-1", "pid": "12x"}))
        self.assertIsNone(session_identity({"connection_id": "srv-1", "pid": 0}))
        self.assertNotEqual(
            session_identity({"connection_id": "srv-1", "pid": 12}),
            session_identity({"connection_id": "srv-2", "pid": 12}),
        )

    def test_selection_requires_exactly_one_matching_process(self):
        row = {"connection_id": "srv-1", "pid": 12, "status": "running"}
        self.assertIs(selected_session([row], "srv-1", "012"), row)
        self.assertIsNone(selected_session([row], "srv-2", 12))
        self.assertIsNone(selected_session([row, dict(row)], "srv-1", 12))
        self.assertIsNone(selected_session([row], "srv-1", None))
        self.assertIsNone(selected_session(None, "srv-1", 12))

    def test_preserve_selection_only_while_unique_identity_remains(self):
        row = {"connection_id": "srv-1", "pid": 12}
        self.assertEqual(preserved_session_identity([row], ("srv-1", "012")), ("srv-1", "12"))
        self.assertIsNone(preserved_session_identity([], ("srv-1", 12)))
        self.assertIsNone(preserved_session_identity([row, dict(row)], ("srv-1", 12)))
        self.assertIsNone(preserved_session_identity([row], ("srv-1", -1)))
        self.assertIsNone(preserved_session_identity([row], "srv-1"))


if __name__ == "__main__":
    unittest.main()
