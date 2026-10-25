"""R114: bounded, opt-in, read-only Grafana dashboard discovery.

Only GET /api/search with type=dash-db is supported. Bearer credentials are
supplied per request, never stored, logged, written to URLs or returned.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import math
import os
import re
import socket
import time
import unicodedata
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_TOKEN_LENGTH = 4096
MAX_QUERY_LENGTH = 120
MAX_DASHBOARDS = 100
_READ_CHUNK = 64 * 1024
_UID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_DNS_HOST = re.compile(r"(?i)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*\.?\Z")
_CONTROL_CATEGORIES = frozenset(("Cc", "Cf", "Cs", "Zl", "Zp"))


class GrafanaError(RuntimeError):
    """Stable, non-sensitive public error code."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _origin(value):
    """Return one canonical HTTPS origin or reject ambiguous URL authorities.

    Bearer tokens are sent to this host, so Unicode lookalikes, URL-encoded
    authorities, non-canonical numeric hosts, and empty query/fragment delimiters
    are rejected before a credential provider can be called. IDNs must be entered
    in their explicit ASCII/punycode form.
    """
    if (not isinstance(value, str) or not value or len(value) > 2048
            or any(ord(char) < 33 or unicodedata.category(char) in _CONTROL_CATEGORIES
                   for char in value)
            or "\\" in value or "%" in value or "?" in value or "#" in value):
        raise GrafanaError("grafana_invalid_https_origin")
    try:
        parsed = urlsplit(value)
        port = parsed.port
        host = parsed.hostname
    except (ValueError, UnicodeError):
        raise GrafanaError("grafana_invalid_https_origin") from None
    if (parsed.scheme.lower() != "https" or not parsed.netloc or not host
            or not host.isascii()
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or (port is not None and not 1 <= port <= 65535)):
        raise GrafanaError("grafana_invalid_https_origin")

    # Canonicalize IP literals and ASCII DNS names rather than preserving
    # untrusted netloc text. Numeric non-IP names are rejected because some
    # resolvers accept legacy integer/octal IPv4 forms.
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        dns_host = host[:-1] if host.endswith(".") else host
        if (not dns_host or len(dns_host) > 253 or ":" in host
                or dns_host.replace(".", "").isdigit()
                or not _DNS_HOST.fullmatch(host)):
            raise GrafanaError("grafana_invalid_https_origin") from None
        canonical_host = dns_host.lower()
    else:
        canonical_host = address.compressed
        if address.version == 6:
            canonical_host = "[" + canonical_host + "]"

    netloc = canonical_host + ((":" + str(port)) if port is not None else "")
    return "https://" + netloc


def _token(value):
    if (not isinstance(value, str) or not value or len(value) > MAX_TOKEN_LENGTH
            or any(ord(char) < 33 or ord(char) > 126 for char in value)):
        raise GrafanaError("grafana_token_required")
    return value


def _visible(value, maximum):
    if not isinstance(value, str):
        return ""
    result = []
    for char in value:
        codepoint = ord(char)
        if (unicodedata.category(char) not in _CONTROL_CATEGORIES
                and not (0xFDD0 <= codepoint <= 0xFDEF)
                and (codepoint & 0xFFFE) != 0xFFFE):
            result.append(char)
    return "".join(result).strip()[:maximum]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("non-finite JSON number")


def _slug(value):
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    result = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return (result or "dashboard")[:80]


def dashboard_link(origin, uid, title="dashboard"):
    """Build a deep link from trusted origin and validated UID, never server URL."""
    base = _origin(origin)
    if not isinstance(uid, str) or not _UID.fullmatch(uid):
        raise GrafanaError("grafana_invalid_dashboard_uid")
    safe_title = _visible(title, 200)
    return base + "/d/" + uid + "/" + _slug(safe_title)


class GrafanaReadOnly:
    """GET-only dashboard discovery with offline default and bounded payloads."""

    def __init__(self, origin, *, opener=None, timeout=5, max_dashboards=MAX_DASHBOARDS):
        self.origin = _origin(origin)
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or not 0 < timeout <= 30):
            raise GrafanaError("grafana_invalid_limits")
        if type(max_dashboards) is not int or not 1 <= max_dashboards <= MAX_DASHBOARDS:
            raise GrafanaError("grafana_invalid_limits")
        self.timeout = float(timeout)
        self.max_dashboards = max_dashboards
        self._opener = opener or build_opener(_RejectRedirects()).open

    def __repr__(self):
        return "<GrafanaReadOnly redacted>"

    def _query(self, query):
        if (not isinstance(query, str) or len(query) > MAX_QUERY_LENGTH
                or any(unicodedata.category(char) in _CONTROL_CATEGORIES
                       for char in query)):
            raise GrafanaError("grafana_invalid_query")
        return query.strip()

    def dashboards(self, *, online=False, token="", query="", cancelled=None):
        """Return an allowlisted dashboard projection; never mutates Grafana."""
        if not online:
            return {"state": "offline", "read_only": True, "count": 0, "dashboards": []}
        if cancelled is not None and not callable(cancelled):
            raise GrafanaError("grafana_invalid_cancellation")

        def check_cancelled():
            if cancelled is not None and cancelled():
                raise GrafanaError("grafana_request_cancelled")

        check_cancelled()
        bearer = _token(token)
        safe_query = self._query(query)
        params = [("type", "dash-db"), ("limit", str(self.max_dashboards))]
        if safe_query:
            params.append(("query", safe_query))
        url = self.origin + "/api/search?" + urlencode(params)
        request = Request(
            url,
            headers={"Authorization": "Bearer " + bearer, "Accept": "application/json"},
            method="GET",
        )
        deadline = time.monotonic() + self.timeout
        try:
            check_cancelled()
            with self._opener(request, timeout=self.timeout) as response:
                if time.monotonic() >= deadline:
                    raise GrafanaError("grafana_deadline_exceeded")
                status = getattr(response, "status", 200)
                if status != 200:
                    raise GrafanaError("grafana_http_failure")
                payload = bytearray()
                while True:
                    check_cancelled()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise GrafanaError("grafana_deadline_exceeded")
                    # urllib's default TLS verification remains enabled. For real
                    # urllib responses, also reduce the socket's inactivity budget
                    # to the remaining request budget when the socket is available.
                    http_response = getattr(response, "fp", None)
                    buffered = getattr(http_response, "fp", None)
                    raw = getattr(buffered, "raw", None)
                    sock = getattr(raw, "_sock", None)
                    if sock is not None:
                        sock.settimeout(remaining)
                    reader = getattr(response, "read1", response.read)
                    chunk = reader(min(_READ_CHUNK, MAX_RESPONSE_BYTES + 1 - len(payload)))
                    # A read that returns after the deadline must not be accepted,
                    # including the final EOF read that would otherwise exit the loop.
                    if time.monotonic() >= deadline:
                        raise GrafanaError("grafana_deadline_exceeded")
                    if not chunk:
                        break
                    payload.extend(chunk)
                    if len(payload) > MAX_RESPONSE_BYTES:
                        raise GrafanaError("grafana_response_too_large")
        except GrafanaError:
            raise
        except HTTPError as exc:
            if 300 <= getattr(exc, "code", 0) < 400:
                raise GrafanaError("grafana_redirect_rejected") from None
            raise GrafanaError("grafana_http_failure") from None
        except Exception:
            # Transport exception strings may contain headers or credentials.
            # When the configured deadline has elapsed, report only that stable code.
            if time.monotonic() >= deadline:
                raise GrafanaError("grafana_deadline_exceeded") from None
            raise GrafanaError("grafana_network_unavailable") from None
        finally:
            bearer = ""

        check_cancelled()
        try:
            data = json.loads(
                bytes(payload).decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
        except (ValueError, UnicodeDecodeError):
            raise GrafanaError("grafana_invalid_json") from None
        if not isinstance(data, list) or len(data) > self.max_dashboards:
            raise GrafanaError("grafana_invalid_response")

        dashboards = []
        seen = set()
        for item in data:
            if not isinstance(item, dict) or item.get("type") != "dash-db":
                raise GrafanaError("grafana_invalid_dashboard")
            uid = item.get("uid")
            if not isinstance(uid, str) or not _UID.fullmatch(uid) or uid in seen:
                raise GrafanaError("grafana_invalid_dashboard_uid")
            title = _visible(item.get("title"), 200)
            if not title:
                raise GrafanaError("grafana_invalid_dashboard")
            raw_tags = item.get("tags", [])
            if not isinstance(raw_tags, list) or len(raw_tags) > 20:
                raise GrafanaError("grafana_invalid_dashboard")
            tags = []
            for tag in raw_tags:
                safe_tag = _visible(tag, 80)
                if not isinstance(tag, str) or not safe_tag:
                    raise GrafanaError("grafana_invalid_dashboard")
                if safe_tag not in tags:
                    tags.append(safe_tag)
            folder = _visible(item.get("folderTitle", ""), 120)
            dashboards.append({
                "uid": uid,
                "title": title,
                "folder": folder,
                "tags": tags,
                "url": dashboard_link(self.origin, uid, title),
            })
            seen.add(uid)
        return {
            "state": "ok",
            "read_only": True,
            "count": len(dashboards),
            "query": safe_query,
            "dashboards": dashboards,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Grafana dashboard discovery; offline by default"
    )
    parser.add_argument("--origin", required=True, help="HTTPS origin only, without path or credentials")
    parser.add_argument("--online", action="store_true", help="Explicitly permit one bounded GET request")
    parser.add_argument("--query", default="", help="Optional dashboard search text (max 120 characters)")
    args = parser.parse_args(argv)
    try:
        client = GrafanaReadOnly(args.origin)
        token = os.environ.get("OPENREMOTE_GRAFANA_TOKEN", "") if args.online else ""
        result = client.dashboards(online=args.online, token=token, query=args.query)
    except GrafanaError as error:
        print(json.dumps({"state": "error", "code": str(error)}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
