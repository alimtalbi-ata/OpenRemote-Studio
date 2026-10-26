"""R129 regression tests for private-key material in incident exports. Author: Abdelhalim Talbi."""
import unittest

from session_incident_center import incident_export


class IncidentExportPrivateKeyRedactionR129Tests(unittest.TestCase):
    def _summary(self, summary):
        return incident_export([{
            "connection_id": "session-r129",
            "protocol": "SSH",
            "diagnostic": {"severity": "error", "summary": summary},
        }])["incidents"][0]["summary"]

    def test_redacts_common_pem_private_key_labels(self):
        labels = (
            "PRIVATE KEY",
            "RSA PRIVATE KEY",
            "EC PRIVATE KEY",
            "OPENSSH PRIVATE KEY",
            "ENCRYPTED PRIVATE KEY",
            "DSA PRIVATE KEY",
        )
        for index, label in enumerate(labels):
            with self.subTest(label=label):
                marker = f"KEY_MATERIAL_SENTINEL_{index}"
                summary = (
                    f"handshake failed\n-----BEGIN {label}-----\n{marker}"
                    f"\n-----END {label}-----\nretry=2"
                )
                safe = self._summary(summary)
                self.assertNotIn(marker, safe)
                self.assertIn("[REDACTED_PRIVATE_KEY_BLOCK]", safe)
                self.assertIn("handshake failed", safe)
                self.assertIn("retry=2", safe)

    def test_redacts_pgp_private_key_block(self):
        marker = "PGP_PRIVATE_MATERIAL_SENTINEL"
        safe = self._summary(
            "signature setup failed\n"
            "-----BEGIN PGP PRIVATE KEY BLOCK-----\n"
            + marker
            + "\n-----END PGP PRIVATE KEY BLOCK-----\nretry=2"
        )
        self.assertNotIn(marker, safe)
        self.assertIn("[REDACTED_PRIVATE_KEY_BLOCK]", safe)
        self.assertIn("retry=2", safe)

    def test_open_or_truncated_private_key_block_fails_closed_to_end(self):
        marker = "PARTIAL_OPENSSH_KEY_SENTINEL"
        safe = self._summary(
            "parser error: -----BEGIN OPENSSH PRIVATE KEY-----\n" + marker
        )
        self.assertNotIn(marker, safe)
        self.assertTrue(safe.endswith("[REDACTED_PRIVATE_KEY_BLOCK]"))

    def test_private_key_header_matching_is_case_insensitive(self):
        marker = "MIXED_CASE_KEY_SENTINEL"
        safe = self._summary(
            "before -----begin rsa private key-----\n"
            + marker
            + "\n-----end rsa private key----- after"
        )
        self.assertNotIn(marker, safe)
        self.assertIn("before", safe)
        self.assertIn("after", safe)


if __name__ == "__main__":
    unittest.main()
