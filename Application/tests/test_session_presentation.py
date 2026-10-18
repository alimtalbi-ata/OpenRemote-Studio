import unittest

from session_presentation import (
    can_reconnect,
    selected_reconnect_allowed,
    session_empty_message,
    session_process_details,
    session_status_label,
    session_visibility_summary,
    session_visual_state,
)


class SessionPresentationTests(unittest.TestCase):
    def test_labels_distinguish_local_process_from_remote_health(self):
        self.assertEqual(session_status_label({"status": "running"}), "Active (processus local)")
        self.assertIn("non vérifiée", session_visual_state({"status": "running"})[1])
        self.assertEqual(session_visual_state({"status": "exited", "exit_code": 0})[0], "completed")
        self.assertEqual(session_visual_state({"status": "exited", "exit_code": 2})[0], "failed")
        self.assertEqual(session_visual_state({"status": "other"})[0], "unknown")

    def test_reconnect_requires_exact_exited_process_and_no_active_sibling(self):
        exited = {"connection_id": "c1", "pid": 10, "status": "exited"}
        self.assertTrue(can_reconnect(exited))
        self.assertTrue(selected_reconnect_allowed([exited], "c1", 10))
        active_sibling = {"connection_id": "c1", "pid": 11, "status": "running"}
        self.assertFalse(selected_reconnect_allowed([exited, active_sibling], "c1", 10))
        self.assertFalse(selected_reconnect_allowed([exited], "c1", None))
        self.assertFalse(selected_reconnect_allowed([exited, dict(exited)], "c1", 10))

    def test_process_details_redact_control_characters_and_sensitive_command(self):
        text = session_process_details({
            "name": "srv\nname", "protocol": "SSH", "pid": 10,
            "status": "running", "started_at": "2026-01-01\x00UTC",
            "command": "ssh -i PRIVATE_KEY", "password": "secret",
        })
        self.assertNotIn("\nname", text)
        self.assertNotIn("\x00", text)
        self.assertNotIn("PRIVATE_KEY", text)
        self.assertNotIn("secret", text)
        self.assertIn("non", text.lower())

    def test_empty_state_and_visibility_summary(self):
        self.assertIn("Aucun processus", session_empty_message(0))
        self.assertIn("filtres", session_empty_message(4, query="missing"))
        self.assertEqual(session_empty_message(3), "")
        self.assertEqual(session_visibility_summary(5, 2), "2 processus affiché(s) sur 5 suivi(s) localement")
        for total, visible in ((-1, 0), (1, -1), (2, 3)):
            with self.assertRaises(ValueError):
                session_visibility_summary(total, visible)

    def test_invalid_details_input_is_rejected(self):
        with self.assertRaises(ValueError):
            session_process_details(None)


if __name__ == "__main__":
    unittest.main()
