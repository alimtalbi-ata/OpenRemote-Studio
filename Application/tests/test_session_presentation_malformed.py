"""Malformed session presentation must never crash the Qt overview."""
import unittest
from session_presentation import session_status_label, session_visual_state, can_reconnect


class MalformedSessionPresentationTests(unittest.TestCase):
    def test_non_mapping_rows_are_unknown(self):
        for row in (None, "", 42, [], False):
            with self.subTest(row=row):
                self.assertEqual(session_status_label(row), "État local inconnu")
                self.assertEqual(session_visual_state(row), ("unknown", "État du processus local inconnu"))
                self.assertFalse(can_reconnect(row))

    def test_running_local_process_does_not_claim_remote_health(self):
        state, label = session_visual_state({"status": "running"})
        self.assertEqual(state, "running")
        self.assertIn("non vérifiée", label)


if __name__ == "__main__":
    unittest.main()
