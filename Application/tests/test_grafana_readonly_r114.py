"""Offline-first Grafana API contract tests. No server or real token is used.
Author: Abdelhalim Talbi.
"""
import io
import json
import os
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from grafana_readonly import GrafanaError, GrafanaReadOnly, dashboard_link, main

ORIGIN = "https://grafana.example.test"
TOKEN = "R114_FAKE_GRAFANA_BEARER_DO_NOT_LOG"


class Reply(io.BytesIO):
    status = 200


class FakeOpen:
    def __init__(self, payload=None, *, status=200, error=None):
        self.payload = json.dumps(payload).encode("utf-8") if payload is not None else b""
        self.status = status
        self.error = error
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error is not None:
            raise self.error
        response = Reply(self.payload)
        response.status = self.status
        return response


def dashboard(uid="cpu_Prod-1", title="CPU / Production", **extra):
    value = {"uid": uid, "title": title, "type": "dash-db",
             "folderTitle": "Operations", "tags": ["prod", "capacity"]}
    value.update(extra)
    return value


class GrafanaReadOnlyR114Tests(unittest.TestCase):
    def test_offline_is_default_and_never_calls_transport(self):
        fake = FakeOpen([dashboard()])
        client = GrafanaReadOnly(ORIGIN, opener=fake)
        result = client.dashboards()
        self.assertEqual(result, {
            "state": "offline", "read_only": True, "count": 0, "dashboards": []
        })
        self.assertEqual(fake.requests, [])

    def test_origin_requires_https_root_without_credentials_or_query(self):
        invalid = (
            "http://grafana.example.test",
            "https://user:password@grafana.example.test",
            "https://grafana.example.test/api",
            "https://grafana.example.test/?token=x",
            "https://grafana.example.test/#fragment",
            "https://grafana.example.test\n",
            "https://grafana.example.test:99999",
        )
        for origin in invalid:
            with self.subTest(origin=origin), self.assertRaises(GrafanaError):
                GrafanaReadOnly(origin)

    def test_origin_rejects_confusable_and_noncanonical_hosts(self):
        # The destination receives a Bearer token. Reject host spellings that
        # can be visually misleading or interpreted inconsistently by resolvers.
        invalid_origins = (
            "https://gr\\u0430fana.example.test",  # Cyrillic 'a', not ASCII a
            "https://%67rafana.example.test",
            "https://grafana_test.example.test",
            "https://grafana..example.test",
            "https://999.999.999.999",
            "https://2130706433",  # legacy integer-form IPv4
            "https://grafana.example.test/?",
            "https://grafana.example.test/#",
            r"https://grafana.example.test\\evil",
        )
        for origin in invalid_origins:
            with self.subTest(origin=repr(origin)), self.assertRaisesRegex(
                    GrafanaError, "grafana_invalid_https_origin"):
                GrafanaReadOnly(origin)

    def test_origin_is_canonical_and_accepts_unambiguous_ip_literals(self):
        self.assertEqual(
            GrafanaReadOnly("HTTPS://GRAFANA.EXAMPLE.TEST.:443/").origin,
            "https://grafana.example.test:443",
        )
        self.assertEqual(
            GrafanaReadOnly("https://127.0.0.1:3000").origin,
            "https://127.0.0.1:3000",
        )
        self.assertEqual(
            GrafanaReadOnly("https://[2001:db8::1]:3000").origin,
            "https://[2001:db8::1]:3000",
        )
    def test_limits_are_strict_and_finite(self):
        for timeout in (0, -1, 30.1, float("inf"), float("nan"), True):
            with self.subTest(timeout=timeout), self.assertRaisesRegex(GrafanaError, "invalid_limits"):
                GrafanaReadOnly(ORIGIN, timeout=timeout)
        for limit in (0, 101, True, 1.5):
            with self.subTest(limit=limit), self.assertRaisesRegex(GrafanaError, "invalid_limits"):
                GrafanaReadOnly(ORIGIN, max_dashboards=limit)

    def test_get_only_bearer_header_and_dashboard_links_are_rebuilt(self):
        fake = FakeOpen([dashboard(url="https://evil.example/steal", slug="../evil")])
        result = GrafanaReadOnly(ORIGIN, opener=fake).dashboards(
            online=True, token=TOKEN, query="CPU services"
        )
        request, timeout = fake.requests[0]
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(headers["authorization"], "Bearer " + TOKEN)
        self.assertEqual(headers["accept"], "application/json")
        self.assertNotIn(TOKEN, request.full_url)
        self.assertLessEqual(timeout, 5)
        parsed = urlsplit(request.full_url)
        self.assertEqual(parsed.netloc, "grafana.example.test")
        self.assertEqual(parse_qs(parsed.query), {
            "type": ["dash-db"], "limit": ["100"], "query": ["CPU services"]
        })
        row = result["dashboards"][0]
        self.assertEqual(row["url"], ORIGIN + "/d/cpu_Prod-1/cpu-production")
        self.assertNotIn("evil.example", json.dumps(result))
        self.assertEqual(set(row), {"uid", "title", "folder", "tags", "url"})
        self.assertTrue(result["read_only"])

    def test_only_safe_projection_and_invisible_display_controls_are_returned(self):
        fake = FakeOpen([dashboard(title="CPU\u202e dashboard", tags=["prod\u202e", "prod", "HA"])])
        row = GrafanaReadOnly(ORIGIN, opener=fake).dashboards(online=True, token=TOKEN)["dashboards"][0]
        self.assertEqual(row["title"], "CPU dashboard")
        self.assertEqual(row["tags"], ["prod", "HA"])
        self.assertNotIn("\u202e", json.dumps(row))

    def test_token_required_before_network_and_never_in_repr(self):
        fake = FakeOpen([dashboard()])
        client = GrafanaReadOnly(ORIGIN, opener=fake)
        with self.assertRaisesRegex(GrafanaError, "token_required"):
            client.dashboards(online=True, token="")
        self.assertEqual(fake.requests, [])
        self.assertNotIn(TOKEN, repr(client))

    def test_malformed_token_is_rejected_before_network(self):
        fake = FakeOpen([dashboard()])
        client = GrafanaReadOnly(ORIGIN, opener=fake)
        for token in ("bad\r\nHeader: injected", "token with spaces", "x" * 4097):
            with self.subTest(token_length=len(token)), self.assertRaisesRegex(GrafanaError, "token_required"):
                client.dashboards(online=True, token=token)
        self.assertEqual(fake.requests, [])

    def test_transport_exception_with_token_is_normalized(self):
        fake = FakeOpen(error=RuntimeError("debug Authorization: Bearer " + TOKEN))
        client = GrafanaReadOnly(ORIGIN, opener=fake)
        with self.assertRaises(GrafanaError) as caught:
            client.dashboards(online=True, token=TOKEN)
        self.assertEqual(str(caught.exception), "grafana_network_unavailable")
        self.assertNotIn(TOKEN, str(caught.exception) + repr(client))

    def test_redirect_is_rejected_without_following_or_disclosing_target(self):
        fake = FakeOpen(error=HTTPError("https://evil.example/?" + TOKEN, 302, "Found", {}, None))
        with self.assertRaisesRegex(GrafanaError, "grafana_redirect_rejected") as caught:
            GrafanaReadOnly(ORIGIN, opener=fake).dashboards(online=True, token=TOKEN)
        self.assertNotIn("evil.example", str(caught.exception))
        self.assertEqual(len(fake.requests), 1)

    def test_non_200_response_is_rejected(self):
        fake = FakeOpen([dashboard()], status=403)
        with self.assertRaisesRegex(GrafanaError, "grafana_http_failure"):
            GrafanaReadOnly(ORIGIN, opener=fake).dashboards(online=True, token=TOKEN)

    def test_response_size_limit_is_enforced(self):
        fake = FakeOpen()
        fake.payload = b" " * (1024 * 1024 + 2)
        with self.assertRaisesRegex(GrafanaError, "grafana_response_too_large"):
            GrafanaReadOnly(ORIGIN, opener=fake).dashboards(online=True, token=TOKEN)

    def test_body_read_returning_after_deadline_is_rejected(self):
        class SlowReply(io.BytesIO):
            status = 200
            def read1(self, size=-1):
                time.sleep(0.025)
                return super().read1(size)

        class SlowOpen:
            def __call__(self, request, timeout):
                self.request = request
                self.timeout = timeout
                return SlowReply(json.dumps([dashboard()]).encode("utf-8"))

        fake = SlowOpen()
        with self.assertRaisesRegex(GrafanaError, "grafana_deadline_exceeded") as caught:
            GrafanaReadOnly(ORIGIN, opener=fake, timeout=0.005).dashboards(
                online=True, token=TOKEN
            )
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_duplicate_json_keys_and_invalid_json_are_rejected(self):
        for payload in (b'{"uid":"x","uid":"y"}', b'NaN', b'not json'):
            fake = FakeOpen()
            fake.payload = payload
            with self.subTest(payload=payload), self.assertRaisesRegex(GrafanaError, "invalid_json"):
                GrafanaReadOnly(ORIGIN, opener=fake).dashboards(online=True, token=TOKEN)

    def test_non_dashboard_wrong_uid_and_duplicate_uid_fail_closed(self):
        cases = (
            [dashboard(extra="x", type="alert-list")],
            [dashboard(uid="../outside")],
            [dashboard(), dashboard()],
            [dashboard(title="\u202e")],
            [dashboard(tags=["x"] * 21)],
            [{"uid": "good", "title": "missing-type"}],
        )
        for data in cases:
            fake = FakeOpen(data)
            with self.subTest(data=data), self.assertRaises(GrafanaError):
                GrafanaReadOnly(ORIGIN, opener=fake).dashboards(online=True, token=TOKEN)

    def test_server_supplied_urls_never_control_dashboard_link(self):
        fake = FakeOpen([dashboard(url="//evil.example/path", title="A dashboard")])
        row = GrafanaReadOnly(ORIGIN, opener=fake).dashboards(online=True, token=TOKEN)["dashboards"][0]
        self.assertEqual(row["url"], dashboard_link(ORIGIN, row["uid"], row["title"]))
        self.assertTrue(row["url"].startswith(ORIGIN + "/d/"))

    def test_cancellation_prevents_transport(self):
        fake = FakeOpen([dashboard()])
        with self.assertRaisesRegex(GrafanaError, "request_cancelled"):
            GrafanaReadOnly(ORIGIN, opener=fake).dashboards(
                online=True, token=TOKEN, cancelled=lambda: True
            )
        self.assertEqual(fake.requests, [])

    def test_invalid_query_is_rejected_without_transport(self):
        fake = FakeOpen([dashboard()])
        for query in ("\nheader", "x" * 121, None):
            with self.subTest(query=str(query)[:20]), self.assertRaisesRegex(GrafanaError, "invalid_query"):
                GrafanaReadOnly(ORIGIN, opener=fake).dashboards(
                    online=True, token=TOKEN, query=query
                )
        self.assertEqual(fake.requests, [])

    def test_cli_is_offline_by_default_and_does_not_read_token(self):
        out = io.StringIO()
        original_get = os.environ.get

        def guarded_get(key, default=None):
            if key == "OPENREMOTE_GRAFANA_TOKEN":
                raise AssertionError("token read offline")
            return original_get(key, default)

        with patch.dict(os.environ, {"OPENREMOTE_GRAFANA_TOKEN": TOKEN}), \
             patch("grafana_readonly.os.environ.get", side_effect=guarded_get), \
             redirect_stdout(out):
            self.assertEqual(main(["--origin", ORIGIN]), 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["state"], "offline")
        self.assertNotIn(TOKEN, out.getvalue())

    def test_dashboard_link_rejects_untrusted_uid(self):
        for uid in ("", "../secret", "a/b", "a?token=x", "x" * 129, None):
            with self.subTest(uid=uid), self.assertRaises(GrafanaError):
                dashboard_link(ORIGIN, uid, "Example")


if __name__ == "__main__":
    unittest.main()
