"""R130 regression tests for prefixed environment-style secret names. Author: Abdelhalim Talbi."""
import unittest

from session_incident_center import incident_export


class IncidentExportPrefixedSecretRedactionR130Tests(unittest.TestCase):
    def _summary(self, summary):
        return incident_export([{
            "connection_id": "session-r130",
            "protocol": "SSH",
            "diagnostic": {"severity": "error", "summary": summary},
        }])["incidents"][0]["summary"]

    def test_redacts_prefixed_and_vendor_specific_secret_names(self):
        summary = (
            "handshake failed "
            "GITHUB_TOKEN=ghp_R130_SENTINEL "
            'NPM_TOKEN="npm R130 secret with spaces" '
            "AWS_SESSION_TOKEN=awsSessionR130Sentinel "
            "AZURE_CLIENT_SECRET: azureClientR130Sentinel "
            "DB_PASSWORD=dbPasswordR130Sentinel "
            "PGPASSWORD=pgPasswordR130Sentinel "
            "AWS_ACCESS_KEY_ID=AKIA_R130_SENTINEL "
            "GITHUB_APP_PRIVATE_KEY=privateKeyR130Sentinel "
            "GOOGLE_APPLICATION_CREDENTIALS=/private/path/r130.json "
            'DOCKER_AUTH_CONFIG={"auths":{"registry":"dockerAuthR130Sentinel"}} '
            "NPM_CONFIG__AUTH=npmAuthR130Sentinel "
            "VAULT_TOKEN=vaultTokenR130Sentinel "
            "DATABASE_URL=postgresql://svc:dbPassR130@db.example/ops "
            "retry_count=3"
        )
        safe = self._summary(summary)
        for sentinel in (
            "ghp_R130_SENTINEL",
            "npm R130 secret with spaces",
            "awsSessionR130Sentinel",
            "azureClientR130Sentinel",
            "dbPasswordR130Sentinel",
            "pgPasswordR130Sentinel",
            "AKIA_R130_SENTINEL",
            "privateKeyR130Sentinel",
            "/private/path/r130.json",
            "dockerAuthR130Sentinel",
            "npmAuthR130Sentinel",
            "vaultTokenR130Sentinel",
            "dbPassR130",
            "db.example",
        ):
            with self.subTest(sentinel=sentinel):
                self.assertNotIn(sentinel, safe)
        self.assertIn("handshake failed", safe)
        self.assertIn("retry_count=3", safe)
        self.assertIn("[REDACTED]", safe)

    def test_redacts_quoted_json_key_but_preserves_other_fields(self):
        safe = self._summary(
            '{"AZURE_CLIENT_SECRET": "jsonSecretR130", '
            '"retry_count": 2, "display_name": "ops"}'
        )
        self.assertNotIn("jsonSecretR130", safe)
        self.assertIn('"AZURE_CLIENT_SECRET": [REDACTED]', safe)
        self.assertIn('"retry_count": 2', safe)
        self.assertIn('"display_name": "ops"', safe)

    def test_keeps_nonsecret_configuration_values(self):
        summary = (
            'RETRY_COUNT=3 REQUEST_TIMEOUT=30 DISPLAY_NAME="operations user" '
            "AUTH_MODE=readonly TOKENIZER=plain HOST_KEY_TYPE=ssh-ed25519"
        )
        self.assertEqual(self._summary(summary), summary)

    def test_prefix_matching_is_case_insensitive_and_not_substring_only(self):
        safe = self._summary(
            "github_token=lowerCaseR130Sentinel "
            "pGpassword=pgLowerR130Sentinel "
            "nPm_CoNfIg__AuTh=authLowerR130Sentinel "
            "TOKENIZER=keep-this"
        )
        for secret in (
            "lowerCaseR130Sentinel",
            "pgLowerR130Sentinel",
            "authLowerR130Sentinel",
        ):
            self.assertNotIn(secret, safe)
        self.assertIn("TOKENIZER=keep-this", safe)


if __name__ == "__main__":
    unittest.main()
