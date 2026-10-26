"""R128 regression tests for secret-safe session incident exports. Author: Abdelhalim Talbi."""
import unittest
from session_incident_center import incident_export


class IncidentExportRedactionR128Tests(unittest.TestCase):
    def _summary(self, summary):
        return incident_export([{
            "connection_id": "session-01",
            "protocol": "SSH",
            "diagnostic": {"severity": "error", "summary": summary},
        }])["incidents"][0]["summary"]

    def test_redacts_assignment_cli_json_and_url_credentials(self):
        summary = (
            "password=hunter2 token:tokenABC --password 'cli secret words' "
            '--api-key=APIKEY-SECRET "client_secret": "JSON SECRET WITH SPACES" '
            "https://operator:urlPasswordSecret@host.example/path"
        )
        safe = self._summary(summary)
        for secret in (
            "hunter2", "tokenABC", "cli secret words", "APIKEY-SECRET",
            "JSON SECRET WITH SPACES", "urlPasswordSecret",
        ):
            self.assertNotIn(secret, safe)
        self.assertIn("[REDACTED]", safe)
        self.assertIn("host.example", safe)

    def test_redacts_bearer_basic_cookie_and_multiple_cookie_values(self):
        summary = (
            "Authorization: Bearer bearerSecretValue; "
            "proxy: Basic basicSecretValue; "
            "Cookie: session=COOKIE_SECRET; refresh=REFRESH_COOKIE_SECRET; path=/"
        )
        safe = self._summary(summary)
        for secret in (
            "bearerSecretValue", "basicSecretValue",
            "COOKIE_SECRET", "REFRESH_COOKIE_SECRET",
        ):
            self.assertNotIn(secret, safe)
        self.assertIn("Cookie=[REDACTED]", safe)

    def test_redacts_standalone_jwt(self):
        token = "eyJhbGciOiJub25lIn0.eyJ1c2VyIjoiYWxpbSJ9.signatureSecretValue"
        safe = self._summary("Request failed with jwt=" + token)
        self.assertNotIn(token, safe)
        self.assertNotIn("signatureSecretValue", safe)
        self.assertIn("[REDACTED_JWT]", safe)

    def test_arbitrary_objects_are_not_stringified(self):
        class HostileValue:
            def __str__(self):
                raise AssertionError("export must not invoke __str__")

            def __repr__(self):
                raise AssertionError("export must not invoke __repr__")

        exported = incident_export([{
            "connection_id": HostileValue(),
            "protocol": "SSH",
            "diagnostic": {"severity": "error", "summary": HostileValue()},
        }])
        self.assertEqual(exported["incidents"][0]["connection_id"], "")
        self.assertEqual(exported["incidents"][0]["summary"], "")

    def test_keeps_useful_nonsensitive_context_and_drops_extra_keys(self):
        item = {
            "connection_id": "host-a",
            "protocol": "SSH",
            "password": "TOP_LEVEL_SECRET",
            "process_args": "--password TOP_LEVEL_SECRET",
            "diagnostic": {
                "severity": "error",
                "summary": "Connection refused after 2 seconds",
            },
        }
        exported = incident_export([item])
        rendered = repr(exported)
        self.assertNotIn("TOP_LEVEL_SECRET", rendered)
        self.assertNotIn("process_args", rendered)
        self.assertIn("Connection refused after 2 seconds", rendered)
        self.assertFalse(exported["incidents"][0]["can_reconnect"])

    def test_drops_control_characters(self):
        exported = incident_export([{
            "connection_id": "host\nInjected",
            "protocol": "SSH",
            "diagnostic": {"summary": "failed\x00connection"},
        }])
        self.assertNotIn("\n", exported["incidents"][0]["connection_id"])
        self.assertNotIn("\x00", exported["incidents"][0]["summary"])


if __name__ == "__main__":
    unittest.main()
