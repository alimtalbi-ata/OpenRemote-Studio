"""R109 Zabbix API safety contract; fake HTTPS transport only.
Author: Abdelhalim Talbi.
"""
import io
import json
import os
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from zabbix_readonly import ZabbixError, ZabbixReadOnly, main

ORIGIN = "https://zabbix.example.test/zabbix"
TOKEN = "R109_FAKE_TOKEN_NEVER_LOG"


class Response(io.BytesIO):
    status = 200
    def __init__(self, body, headers=None):
        super().__init__(body if isinstance(body, bytes) else json.dumps(body).encode("utf-8"))
        self.headers = headers or {"Content-Length": str(len(self.getvalue())), "Content-Type": "application/json"}


def envelope(result, *, request_id=1, error=None):
    data = {"jsonrpc": "2.0", "id": request_id}
    if error is None:
        data["result"] = result
    else:
        data["error"] = error
    return data


def problems(*rows):
    return envelope(list(rows))


def problem(eventid="101", objectid="501", name="Disk space low", severity="4", clock="1790000000", acknowledged="0"):
    return {"eventid": eventid, "objectid": objectid, "name": name,
            "severity": severity, "clock": clock, "acknowledged": acknowledged}


def triggers(*rows):
    return envelope(list(rows))


def trigger(triggerid="501", description="Disk threshold", hosts=None):
    return {"triggerid": triggerid, "description": description,
            "hosts": hosts if hosts is not None else [{"hostid": "9", "host": "srv01", "name": "SRV01"}]}


class FakeOpen:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if hasattr(item, "read") else Response(item)


class ZabbixReadOnlyR109Tests(unittest.TestCase):
    def test_offline_default_never_calls_transport(self):
        fake = FakeOpen()
        client = ZabbixReadOnly(ORIGIN, opener=fake)
        result = client.problems()
        self.assertEqual(result["state"], "offline")
        self.assertTrue(result["read_only"])
        self.assertEqual(fake.requests, [])

    def test_https_origin_validation_and_base_path(self):
        client = ZabbixReadOnly(ORIGIN)
        self.assertEqual(client.endpoint, "https://zabbix.example.test/zabbix/api_jsonrpc.php")
        self.assertEqual(ZabbixReadOnly("https://zabbix.example.test/zabbix/api_jsonrpc.php").endpoint,
                         "https://zabbix.example.test/zabbix/api_jsonrpc.php")
        invalid = ("http://zabbix.example.test", "https://user:pass@zabbix.example.test",
                   "https://zabbix.example.test/?token=x", "https://zabbix.example.test/#x",
                   "https://zabbix.example.test/../api", "https://zabbix.example.test/%2e%2e",
                   "https://zabbix.example.test/a//b", "https://bad host", "https://zabbix.example.test\n")
        for origin in invalid:
            with self.subTest(origin=origin), self.assertRaisesRegex(ZabbixError, "invalid_https_origin"):
                ZabbixReadOnly(origin)

    def test_two_read_methods_return_whitelisted_active_problem_and_host(self):
        fake = FakeOpen(
            problems(problem()),
            triggers(trigger()),
        )
        client = ZabbixReadOnly(ORIGIN, opener=fake, timeout=4, max_problems=20)
        result = client.problems(online=True, token=TOKEN)
        self.assertEqual(result["state"], "ok")
        self.assertTrue(result["read_only"])
        self.assertEqual(len(result["problems"]), 1)
        row = result["problems"][0]
        self.assertEqual(row["event_id"], "101")
        self.assertEqual(row["severity"], 4)
        self.assertEqual(row["severity_label"], "Haute")
        self.assertFalse(row["acknowledged"])
        self.assertEqual(row["hosts"], [{"host": "srv01", "name": "SRV01"}])
        self.assertEqual([req.get_method() for req, _ in fake.requests], ["POST", "POST"])
        payloads = [json.loads(req.data.decode("utf-8")) for req, _ in fake.requests]
        self.assertEqual([p["method"] for p in payloads], ["problem.get", "trigger.get"])
        self.assertTrue(all("auth" not in p and TOKEN not in req.data.decode("utf-8")
                            for p, (req, _) in zip(payloads, fake.requests)))
        self.assertTrue(all(req.get_header("Authorization") == "Bearer " + TOKEN
                            for req, _ in fake.requests))
        self.assertEqual([timeout for _, timeout in fake.requests], [4.0, 4.0])
        self.assertNotIn(TOKEN, repr(client))

    def test_empty_problem_list_skips_trigger_request(self):
        fake = FakeOpen(problems())
        result = ZabbixReadOnly(ORIGIN, opener=fake).problems(online=True, token=TOKEN)
        self.assertEqual(result["problems"], [])
        self.assertEqual(len(fake.requests), 1)

    def test_token_missing_or_malformed_blocks_network(self):
        for token in ("", "x\ny", "x\x00y", "x" * 4097):
            fake = FakeOpen()
            with self.subTest(token_length=len(token)), self.assertRaisesRegex(ZabbixError, "token_required"):
                ZabbixReadOnly(ORIGIN, opener=fake).problems(online=True, token=token)
            self.assertEqual(fake.requests, [])

    def test_only_allowlisted_api_methods_are_callable(self):
        fake = FakeOpen()
        client = ZabbixReadOnly(ORIGIN, opener=fake)
        with self.assertRaisesRegex(ZabbixError, "method_not_allowed"):
            client._call("event.acknowledge", {}, token=TOKEN)
        with self.assertRaisesRegex(ZabbixError, "method_not_allowed"):
            client._call("host.create", {}, token=TOKEN)
        self.assertEqual(fake.requests, [])

    def test_api_error_does_not_echo_untrusted_body(self):
        secret = "API_BODY_SECRET_R109"
        fake = FakeOpen(envelope([], error={"code": -32602, "message": secret, "data": secret}))
        with self.assertRaisesRegex(ZabbixError, "api_error") as caught:
            ZabbixReadOnly(ORIGIN, opener=fake).problems(online=True, token=TOKEN)
        self.assertNotIn(secret, str(caught.exception))

    def test_http_auth_and_redirect_failures_are_neutral(self):
        for status, expected in ((401, "auth_or_permission_denied"), (403, "auth_or_permission_denied"),
                                 (302, "redirect_rejected"), (429, "rate_limited")):
            fake = FakeOpen(HTTPError("https://zabbix.invalid", status, "token=HIDDEN", {}, None))
            with self.subTest(status=status), self.assertRaisesRegex(ZabbixError, expected):
                ZabbixReadOnly(ORIGIN, opener=fake).problems(online=True, token=TOKEN)

    def test_transport_error_is_redacted(self):
        secret = "NETWORK_SECRET_R109"
        fake = FakeOpen(URLError("failed with " + secret))
        with self.assertRaisesRegex(ZabbixError, "network_unavailable") as caught:
            ZabbixReadOnly(ORIGIN, opener=fake).problems(online=True, token=TOKEN)
        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn(TOKEN, repr(caught.exception))

    def test_duplicate_keys_nan_wrong_id_and_bad_payload_rejected(self):
        bad_responses = (
            Response(b'{"jsonrpc":"2.0","id":1,"id":1,"result":[]}'),
            Response(b'{"jsonrpc":"2.0","id":1,"result":[NaN]}'),
            Response(envelope([], request_id=True)),
            Response(envelope({"not": "a list"})),
        )
        for response in bad_responses:
            with self.subTest(body=response.getvalue()[:40]), self.assertRaises(ZabbixError):
                ZabbixReadOnly(ORIGIN, opener=FakeOpen(response)).problems(online=True, token=TOKEN)

    def test_oversized_body_rejected_before_json_decode(self):
        fake = FakeOpen(Response(b" " * (1024 * 1024 + 1)))
        with self.assertRaisesRegex(ZabbixError, "response_too_large"):
            ZabbixReadOnly(ORIGIN, opener=fake).problems(online=True, token=TOKEN)

    def test_result_limit_and_duplicate_ids_fail_closed(self):
        fake = FakeOpen(problems(problem("101"), problem("101", "502")))
        with self.assertRaisesRegex(ZabbixError, "invalid_response"):
            ZabbixReadOnly(ORIGIN, opener=fake, max_problems=2).problems(online=True, token=TOKEN)
        over_limit = FakeOpen(problems(problem("101"), problem("102")))
        with self.assertRaisesRegex(ZabbixError, "invalid_response"):
            ZabbixReadOnly(ORIGIN, opener=over_limit, max_problems=1).problems(online=True, token=TOKEN)

    def test_cancelled_before_request_does_not_call_transport(self):
        fake = FakeOpen()
        with self.assertRaisesRegex(ZabbixError, "request_cancelled"):
            ZabbixReadOnly(ORIGIN, opener=fake).problems(
                online=True, token=TOKEN, cancelled=lambda: True)
        self.assertEqual(fake.requests, [])

    def test_cancel_between_problem_and_trigger_call_stops_second_request(self):
        fake = FakeOpen(problems(problem()))
        calls = {"n": 0}
        def cancelled():
            calls["n"] += 1
            return calls["n"] >= 3
        with self.assertRaisesRegex(ZabbixError, "request_cancelled"):
            ZabbixReadOnly(ORIGIN, opener=fake).problems(
                online=True, token=TOKEN, cancelled=cancelled)
        self.assertEqual(len(fake.requests), 1)

    def test_unsafe_unicode_display_and_invalid_ranges_rejected(self):
        bad_rows = (
            problem(name="hide\u202eexe.exe"),
            problem(severity="6"),
            problem(clock="9999999999"),
            problem(acknowledged="2"),
        )
        for row in bad_rows:
            with self.subTest(row=row), self.assertRaises(ZabbixError):
                ZabbixReadOnly(ORIGIN, opener=FakeOpen(problems(row))).problems(
                    online=True, token=TOKEN)

    def test_cli_offline_never_reads_token_or_network(self):
        from contextlib import redirect_stdout
        import io
        output = io.StringIO()
        # Building an urllib opener is inert; offline mode must never call it.
        # The backend offline contract is separately covered by FakeOpen above.
        with patch.dict(os.environ, {"OPENREMOTE_ZABBIX_TOKEN": TOKEN}), redirect_stdout(output):
            self.assertEqual(main(["--origin", ORIGIN]), 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "offline")
        self.assertNotIn(TOKEN, output.getvalue())


if __name__ == "__main__":
    unittest.main()
