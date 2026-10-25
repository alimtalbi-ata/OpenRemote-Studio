"""R109: bounded, explicit, read-only Zabbix problem triage API.

Only problem.get and trigger.get are implemented. The API token is passed per
request, never stored on the client, never included in JSON-RPC parameters, and
never included in public errors. TLS verification is the urllib default.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import unicodedata
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_TOKEN_LENGTH = 4096
_ALLOWED_API_METHODS = frozenset(("problem.get", "trigger.get"))
_SEVERITY_LABELS = (
    "Non classée", "Information", "Avertissement", "Moyenne", "Haute", "Désastre"
)
_CONTROL_CATEGORIES = frozenset(("Cc", "Cf", "Cs", "Zl", "Zp"))


class ZabbixError(RuntimeError):
    """Stable error code safe for UI/CLI display; never contains server text."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _endpoint(origin: str) -> str:
    if (not isinstance(origin, str) or not origin or len(origin) > 512
            or any(ord(char) < 33 or ord(char) == 127 for char in origin)
            or "\\" in origin or "%" in origin):
        raise ZabbixError("zabbix_invalid_https_origin")
    try:
        parts = urlsplit(origin)
        host = parts.hostname
        port = parts.port
    except (ValueError, UnicodeError):
        raise ZabbixError("zabbix_invalid_https_origin") from None
    if (parts.scheme.lower() != "https" or not host or not host.isascii()
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or not parts.netloc):
        raise ZabbixError("zabbix_invalid_https_origin")
    if port is not None and not 1 <= port <= 65535:
        raise ZabbixError("zabbix_invalid_https_origin")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if ":" in host or not re.fullmatch(
            r"(?i)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*\.?",
            host,
        ):
            raise ZabbixError("zabbix_invalid_https_origin") from None
    path = parts.path or ""
    if len(path) > 256 or (path and not path.startswith("/")):
        raise ZabbixError("zabbix_invalid_https_origin")
    segments = path.split("/")[1:] if path else []
    if any(not segment or segment in (".", "..")
           or not re.fullmatch(r"[A-Za-z0-9._~-]+", segment) for segment in segments):
        raise ZabbixError("zabbix_invalid_https_origin")
    if any(segment.casefold() == "api_jsonrpc.php" for segment in segments[:-1]):
        raise ZabbixError("zabbix_invalid_https_origin")
    if segments and segments[-1].casefold() == "api_jsonrpc.php":
        api_path = path
    else:
        api_path = path.rstrip("/") + "/api_jsonrpc.php"
    endpoint = f"https://{parts.netloc}{api_path}"
    if len(endpoint) > 600:
        raise ZabbixError("zabbix_invalid_https_origin")
    return endpoint


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON property")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("non-finite JSON number")


def _validate_json_depth(value, maximum=24):
    stack = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if depth > maximum or nodes > 100_000:
            raise ValueError("JSON structure too complex")
        if isinstance(current, dict):
            stack.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)


def _safe_text(value, maximum=512):
    if not isinstance(value, str) or len(value) > maximum:
        raise ZabbixError("zabbix_invalid_response")
    for char in value:
        code = ord(char)
        if (unicodedata.category(char) in _CONTROL_CATEGORIES
                or 0xFDD0 <= code <= 0xFDEF
                or (code & 0xFFFE) == 0xFFFE):
            raise ZabbixError("zabbix_invalid_response")
    return value.strip()


def _uint(value, *, maximum=(2**64 - 1), minimum=0):
    if type(value) is int:
        number = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 20:
        number = int(value)
    else:
        raise ZabbixError("zabbix_invalid_response")
    if not minimum <= number <= maximum:
        raise ZabbixError("zabbix_invalid_response")
    return number


def _problem(row):
    if not isinstance(row, dict):
        raise ZabbixError("zabbix_invalid_response")
    event_id = _uint(row.get("eventid"), minimum=1)
    trigger_id = _uint(row.get("objectid"), minimum=1)
    severity = _uint(row.get("severity"), maximum=5)
    timestamp = _uint(row.get("clock"), maximum=4_102_444_800)
    acknowledged = _uint(row.get("acknowledged"), maximum=1)
    name = _safe_text(row.get("name"), 512)
    if not name:
        raise ZabbixError("zabbix_invalid_response")
    return {
        "event_id": str(event_id), "trigger_id": str(trigger_id),
        "name": name, "severity": severity,
        "severity_label": _SEVERITY_LABELS[severity],
        "last_change": timestamp, "acknowledged": bool(acknowledged),
        "hosts": [],
    }


def _trigger(row):
    if not isinstance(row, dict):
        raise ZabbixError("zabbix_invalid_response")
    trigger_id = str(_uint(row.get("triggerid"), minimum=1))
    description = _safe_text(row.get("description", ""), 512)
    raw_hosts = row.get("hosts", [])
    if not isinstance(raw_hosts, list) or len(raw_hosts) > 32:
        raise ZabbixError("zabbix_invalid_response")
    hosts = []
    seen = set()
    for item in raw_hosts:
        if not isinstance(item, dict):
            raise ZabbixError("zabbix_invalid_response")
        technical = _safe_text(item.get("host", ""), 255)
        visible = _safe_text(item.get("name", ""), 255)
        technical = technical or visible
        visible = visible or technical
        if not technical or not visible:
            raise ZabbixError("zabbix_invalid_response")
        key = (technical.casefold(), visible.casefold())
        if key not in seen:
            hosts.append({"host": technical, "name": visible})
            seen.add(key)
    return {"trigger_id": trigger_id, "description": description, "hosts": hosts}


class ZabbixReadOnly:
    """Read active Zabbix problems using a strict allowlist and bounded HTTPS."""

    def __init__(self, origin, *, opener=None, timeout=5, max_problems=50):
        self.endpoint = _endpoint(origin)
        if not (type(timeout) in (int, float) and 0 < timeout <= 30):
            raise ZabbixError("zabbix_invalid_limits")
        if type(max_problems) is not int or not 1 <= max_problems <= 100:
            raise ZabbixError("zabbix_invalid_limits")
        self.timeout = float(timeout)
        self.max_problems = max_problems
        self._opener = opener or build_opener(_RejectRedirects()).open

    def __repr__(self):
        return "<ZabbixReadOnly redacted>"

    @staticmethod
    def _check_cancelled(cancelled):
        if cancelled is not None and cancelled():
            raise ZabbixError("zabbix_request_cancelled")

    @staticmethod
    def _validate_token(token):
        if (not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH
                or any(ord(char) < 33 or ord(char) == 127 for char in token)):
            raise ZabbixError("zabbix_token_required")
        return token

    @staticmethod
    def _http_error_code(status):
        if status in (301, 302, 303, 307, 308):
            return "zabbix_redirect_rejected"
        if status in (401, 403):
            return "zabbix_auth_or_permission_denied"
        if status == 429:
            return "zabbix_rate_limited"
        return "zabbix_network_unavailable"

    def _call(self, method, params, *, token, cancelled=None):
        if method not in _ALLOWED_API_METHODS:
            raise ZabbixError("zabbix_method_not_allowed")
        if not isinstance(params, dict):
            raise ZabbixError("zabbix_invalid_request")
        self._check_cancelled(cancelled)
        body = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
            ensure_ascii=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        request = Request(
            self.endpoint, data=body,
            headers={"Content-Type": "application/json-rpc", "Accept": "application/json",
                     "Authorization": "Bearer " + token},
            method="POST",
        )
        try:
            response = self._opener(request, timeout=self.timeout)
            with response:
                status = getattr(response, "status", getattr(response, "code", 200))
                if status != 200:
                    raise ZabbixError(self._http_error_code(status))
                headers = getattr(response, "headers", {})
                length = headers.get("Content-Length") if hasattr(headers, "get") else None
                if length is not None:
                    if not isinstance(length, str) or not length.isascii() or not length.isdecimal():
                        raise ZabbixError("zabbix_invalid_response")
                    if int(length) > MAX_RESPONSE_BYTES:
                        raise ZabbixError("zabbix_response_too_large")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except ZabbixError:
            raise
        except HTTPError as exc:
            code = self._http_error_code(exc.code)
            try:
                exc.close()
            except Exception:
                pass
            raise ZabbixError(code) from None
        except Exception:
            raise ZabbixError("zabbix_network_unavailable") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ZabbixError("zabbix_response_too_large")
        self._check_cancelled(cancelled)
        try:
            decoded = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                                 parse_constant=_reject_constant)
            _validate_json_depth(decoded)
        except Exception:
            raise ZabbixError("zabbix_invalid_response") from None
        if (not isinstance(decoded, dict) or decoded.get("jsonrpc") != "2.0"
                or type(decoded.get("id")) is not int or decoded.get("id") != 1
                or "result" not in decoded or "error" in decoded):
            raise ZabbixError("zabbix_api_error")
        return decoded["result"]

    def problems(self, *, online=False, token="", limit=None, cancelled=None):
        """Return active, trigger-backed problems; offline mode performs no I/O."""
        if not online:
            return {"state": "offline", "read_only": True, "problems": [],
                    "limit": self.max_problems, "may_be_truncated": False}
        if cancelled is not None and not callable(cancelled):
            raise ZabbixError("zabbix_invalid_cancellation")
        self._check_cancelled(cancelled)
        token = self._validate_token(token)
        requested_limit = self.max_problems if limit is None else limit
        if type(requested_limit) is not int or not 1 <= requested_limit <= self.max_problems:
            raise ZabbixError("zabbix_invalid_limits")
        raw_problems = self._call("problem.get", {
            "output": ["eventid", "name", "severity", "clock", "acknowledged", "objectid"],
            "source": 0, "object": 0,
            "sortfield": "eventid", "sortorder": "DESC", "limit": requested_limit,
        }, token=token, cancelled=cancelled)
        if not isinstance(raw_problems, list) or len(raw_problems) > requested_limit:
            raise ZabbixError("zabbix_invalid_response")
        problems = [_problem(row) for row in raw_problems]
        if len({row["event_id"] for row in problems}) != len(problems):
            raise ZabbixError("zabbix_invalid_response")
        trigger_ids = sorted({row["trigger_id"] for row in problems}, key=int)
        trigger_map = {}
        if trigger_ids:
            self._check_cancelled(cancelled)
            raw_triggers = self._call("trigger.get", {
                "output": ["triggerid", "description"],
                "triggerids": trigger_ids, "selectHosts": ["hostid", "host", "name"],
                "limit": requested_limit,
            }, token=token, cancelled=cancelled)
            if not isinstance(raw_triggers, list) or len(raw_triggers) > requested_limit:
                raise ZabbixError("zabbix_invalid_response")
            for raw in raw_triggers:
                item = _trigger(raw)
                if item["trigger_id"] not in trigger_ids or item["trigger_id"] in trigger_map:
                    raise ZabbixError("zabbix_invalid_response")
                trigger_map[item["trigger_id"]] = item
        for problem in problems:
            trigger = trigger_map.get(problem["trigger_id"], {})
            problem["hosts"] = list(trigger.get("hosts", []))
            problem["trigger_description"] = trigger.get("description", "")
        self._check_cancelled(cancelled)
        return {"state": "ok", "read_only": True, "problems": problems,
                "limit": requested_limit, "may_be_truncated": len(problems) == requested_limit}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zabbix active problems (read-only; offline by default)")
    parser.add_argument("--origin", required=True, help="HTTPS origin or Zabbix base path; never include a token")
    parser.add_argument("--online", action="store_true", help="Explicitly permit bounded HTTPS JSON-RPC reads")
    parser.add_argument("--limit", type=int, default=50, help="Maximum active problems (1..100)")
    args = parser.parse_args(argv)
    try:
        client = ZabbixReadOnly(args.origin, max_problems=args.limit)
        if not args.online:
            result = client.problems()
        else:
            # Environment is consulted only after explicit --online and URL validation.
            token = os.environ.get("OPENREMOTE_ZABBIX_TOKEN", "")
            try:
                result = client.problems(online=True, token=token, limit=args.limit)
            finally:
                token = ""
    except ZabbixError as exc:
        result = {"state": "error", "read_only": True, "code": str(exc), "problems": []}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("state") in ("offline", "ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
