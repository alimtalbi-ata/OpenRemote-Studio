"""R109: bounded, explicit, read-only Zabbix problem triage API.

Only problem.get and trigger.get are implemented. The API token is passed per
request, never stored on the client, never included in JSON-RPC parameters, and
never included in public errors. TLS verification is the urllib default.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import os
import re
import socket
import threading
import time
import unicodedata
from contextvars import ContextVar
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_TOKEN_LENGTH = 4096
_RESPONSE_READ_CHUNK = 64 * 1024
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


# urllib passes a socket inactivity timeout to http.client. These per-request
# context variables let the default HTTPS handler carry one absolute deadline
# through connect, TLS, status/headers and response-body reads.
_ACTIVE_HTTP_DEADLINE = ContextVar("openremote_zabbix_http_deadline", default=None)
_ACTIVE_HTTP_CONNECTION = ContextVar("openremote_zabbix_http_connection", default=None)


class _DeadlineHTTPResponse(http.client.HTTPResponse):
    """HTTPResponse that keeps its owner reachable after urllib closes h.sock."""

    def __init__(self, sock, *args, **kwargs):
        super().__init__(sock, *args, **kwargs)
        self._deadline_sock = sock
        self._deadline_owner = _ACTIVE_HTTP_CONNECTION.get()
        if self._deadline_owner is not None:
            self._deadline_owner._deadline_response = self

    def close(self):
        owner = getattr(self, "_deadline_owner", None)
        try:
            super().close()
        finally:
            if owner is not None:
                owner._response_closed(self)


class _DeadlineHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection whose watchdog closes a transaction at one deadline.

    The timer is armed before network activity. It shuts down both an in-flight
    connect socket and the response socket, including while urllib is parsing a
    slow status line/header. urllib deliberately closes the connection object's
    socket after getresponse(), so the response keeps an explicit socket reference
    until it is closed. The default SSLContext/certificate validation is retained.
    """

    response_class = _DeadlineHTTPResponse

    def __init__(self, *args, **kwargs):
        self._deadline = _ACTIVE_HTTP_DEADLINE.get()
        self._deadline_timer = None
        self._deadline_expired = False
        self._deadline_pending_sock = None
        self._deadline_response = None
        self._deadline_in_getresponse = False
        super().__init__(*args, **kwargs)
        if self._deadline is not None:
            remaining = self._remaining_deadline()
            try:
                configured_timeout = float(self.timeout)
            except (TypeError, ValueError):
                configured_timeout = remaining
            self.timeout = min(configured_timeout, remaining)
            self._deadline_timer = threading.Timer(remaining, self._expire_deadline)
            self._deadline_timer.daemon = True
            self._deadline_timer.start()

    def _remaining_deadline(self):
        if self._deadline is None:
            return self.timeout
        remaining = self._deadline - time.monotonic()
        if self._deadline_expired or remaining <= 0:
            self._expire_deadline()
            raise socket.timeout("Zabbix HTTPS transaction deadline exceeded")
        return remaining

    @staticmethod
    def _shutdown_socket(sock):
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass

    def _expire_deadline(self):
        self._deadline_expired = True
        self._shutdown_socket(self._deadline_pending_sock)
        self._shutdown_socket(self.sock)
        response = self._deadline_response
        if response is not None:
            self._shutdown_socket(getattr(response, "_deadline_sock", None))

    def _cancel_deadline_timer(self):
        timer = self._deadline_timer
        if timer is not None:
            timer.cancel()
            self._deadline_timer = None

    def _response_closed(self, response):
        if self._deadline_response is response:
            self._deadline_response = None
        self._cancel_deadline_timer()

    def _create_connection(self, address, timeout, source_address):
        # Use a fresh remaining budget for each address. DNS resolution itself is
        # performed by the platform resolver and cannot be forcibly interrupted;
        # the deadline is rechecked immediately when it returns.
        if self._deadline is None:
            return socket.create_connection(address, timeout, source_address)
        host, port = address
        last_error = None
        for family, socktype, proto, _canonname, sockaddr in socket.getaddrinfo(
                host, port, type=socket.SOCK_STREAM):
            remaining = self._remaining_deadline()
            sock = socket.socket(family, socktype, proto)
            self._deadline_pending_sock = sock
            try:
                sock.settimeout(remaining)
                if source_address:
                    sock.bind(source_address)
                sock.settimeout(self._remaining_deadline())
                sock.connect(sockaddr)
                self._remaining_deadline()
                # Keep the pending reference until connect() has installed the
                # socket on the connection and completed TLS setup. The watchdog
                # can then close it even during the hand-off window.
                return sock
            except OSError as exc:
                last_error = exc
                self._shutdown_socket(sock)
                self._deadline_pending_sock = None
                if self._deadline_expired or time.monotonic() >= self._deadline:
                    self._expire_deadline()
                    raise socket.timeout("Zabbix HTTPS transaction deadline exceeded") from None
        if last_error is not None:
            raise last_error
        raise OSError("address resolution returned no endpoints")

    def connect(self):
        if self._deadline is None:
            return super().connect()
        self.timeout = self._remaining_deadline()
        # Run the plain HTTP connect/tunnel phase first; its _create_connection
        # override accounts for each address and keeps the in-flight socket
        # reachable by the watchdog.
        http.client.HTTPConnection.connect(self)
        server_hostname = self._tunnel_host or self.host
        # Defer TLS handshake until the SSLSocket is assigned to self.sock. That
        # lets the deadline watchdog shutdown the live TLS socket during a stalled
        # handshake instead of only closing the now-detached raw socket.
        self.sock = self._context.wrap_socket(
            self.sock, server_hostname=server_hostname, do_handshake_on_connect=False
        )
        remaining = self._remaining_deadline()
        self.sock.settimeout(remaining)
        self.sock.do_handshake()
        remaining = self._remaining_deadline()
        self.sock.settimeout(remaining)
        self._deadline_pending_sock = None

    def send(self, data):
        if self._deadline is not None:
            remaining = self._remaining_deadline()
            if self.sock is not None:
                self.sock.settimeout(remaining)
        return super().send(data)

    def getresponse(self):
        if self._deadline is not None:
            self._remaining_deadline()
        self._deadline_in_getresponse = True
        connection_token = _ACTIVE_HTTP_CONNECTION.set(self)
        try:
            response = super().getresponse()
        except Exception:
            raise
        finally:
            _ACTIVE_HTTP_CONNECTION.reset(connection_token)
            self._deadline_in_getresponse = False
        response._deadline_owner = self
        self._deadline_response = response
        try:
            self._remaining_deadline()
        except Exception:
            response.close()
            raise
        return response

    def close(self):
        # http.client closes the connection internally for Connection: close while
        # getresponse() is still constructing the response. Do not cancel its
        # watchdog until the response body itself has been closed.
        if not self._deadline_in_getresponse and self._deadline_response is None:
            self._cancel_deadline_timer()
            pending = self._deadline_pending_sock
            self._deadline_pending_sock = None
            self._shutdown_socket(pending)
        super().close()


class _DeadlineHTTPSHandler(HTTPSHandler):
    """Default HTTPS handler with an absolute transaction deadline watchdog."""

    def https_open(self, req):
        return self.do_open(
            _DeadlineHTTPSConnection, req,
            context=self._context,
        )


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


def _response_socket(response):
    """Find urllib's underlying socket without depending on one wrapper depth."""
    pending = [response]
    visited = set()
    while pending and len(visited) < 64:
        current = pending.pop()
        identity = id(current)
        if identity in visited:
            continue
        visited.add(identity)
        try:
            settimeout = getattr(current, "settimeout", None)
            recv = getattr(current, "recv", None)
            if callable(settimeout) and callable(recv):
                return current
        except Exception:
            pass
        for attribute in ("fp", "raw", "_sock", "sock"):
            try:
                child = getattr(current, attribute, None)
            except Exception:
                child = None
            if child is not None and id(child) not in visited:
                pending.append(child)
    return None


def _read_response_bounded(response, timeout, *, cancelled=None, clock=None, deadline=None):
    """Stream a response under a monotonic body deadline, with cancellation checks.

    A caller may provide the absolute transaction deadline established before
    HTTPS open; this prevents response processing from receiving a fresh budget
    after slow connect/TLS/status/header phases. A peer that continually drips
    body bytes cannot reset the deadline: apply the remaining budget to the socket
    before each read1() and stop if the monotonic deadline is reached.
    """
    clock = clock or time.monotonic
    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        raise ZabbixError("zabbix_invalid_limits") from None
    if not 0 < timeout <= 30:
        raise ZabbixError("zabbix_invalid_limits")
    if deadline is None:
        deadline = clock() + timeout
    elif not isinstance(deadline, (int, float)) or isinstance(deadline, bool):
        raise ZabbixError("zabbix_invalid_limits")
    if deadline <= clock():
        raise ZabbixError("zabbix_timeout")

    # urllib.response.addinfourl wraps http.client.HTTPResponse in .fp. read1()
    # reads at most the available chunk; response.read(n) may try to fill n bytes.
    source = getattr(response, "fp", None)
    if source is None:
        source = response
    reader = getattr(source, "read1", None)
    if not callable(reader):
        reader = getattr(response, "read1", None)
    if not callable(reader):
        reader = getattr(response, "read", None)
    if not callable(reader):
        raise ZabbixError("zabbix_invalid_response")

    network_socket = _response_socket(response)
    content = bytearray()
    while True:
        if cancelled is not None and cancelled():
            raise ZabbixError("zabbix_request_cancelled")
        remaining = deadline - clock()
        if remaining <= 0:
            raise ZabbixError("zabbix_timeout")
        if network_socket is not None:
            try:
                network_socket.settimeout(remaining)
            except Exception:
                # Do not continue with a socket whose deadline could not be applied.
                raise ZabbixError("zabbix_timeout_enforcement_failed") from None
        amount = min(_RESPONSE_READ_CHUNK, MAX_RESPONSE_BYTES + 1 - len(content))
        try:
            chunk = reader(amount)
        except (socket.timeout, TimeoutError):
            raise ZabbixError("zabbix_timeout") from None
        if cancelled is not None and cancelled():
            raise ZabbixError("zabbix_request_cancelled")
        if clock() >= deadline:
            raise ZabbixError("zabbix_timeout")
        if not isinstance(chunk, (bytes, bytearray)):
            raise ZabbixError("zabbix_invalid_response")
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_RESPONSE_BYTES:
            raise ZabbixError("zabbix_response_too_large")
    return bytes(content)


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
        self._opener = opener or build_opener(_RejectRedirects(), _DeadlineHTTPSHandler()).open

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
        deadline = time.monotonic() + self.timeout
        deadline_token = _ACTIVE_HTTP_DEADLINE.set(deadline)
        try:
            try:
                response = self._opener(request, timeout=self.timeout)
                if time.monotonic() >= deadline:
                    try:
                        response.close()
                    except Exception:
                        pass
                    raise ZabbixError("zabbix_timeout")
                with response:
                    status = getattr(response, "status", getattr(response, "code", 200))
                    if time.monotonic() >= deadline:
                        raise ZabbixError("zabbix_timeout")
                    if status != 200:
                        raise ZabbixError(self._http_error_code(status))
                    headers = getattr(response, "headers", {})
                    length = headers.get("Content-Length") if hasattr(headers, "get") else None
                    if length is not None:
                        if not isinstance(length, str) or not length.isascii() or not length.isdecimal():
                            raise ZabbixError("zabbix_invalid_response")
                        if int(length) > MAX_RESPONSE_BYTES:
                            raise ZabbixError("zabbix_response_too_large")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ZabbixError("zabbix_timeout")
                    raw = _read_response_bounded(
                        response, remaining, cancelled=cancelled, deadline=deadline
                    )
            except ZabbixError:
                raise
            except HTTPError as exc:
                if time.monotonic() >= deadline:
                    raise ZabbixError("zabbix_timeout") from None
                code = self._http_error_code(exc.code)
                try:
                    exc.close()
                except Exception:
                    pass
                raise ZabbixError(code) from None
            except Exception as exc:
                reason = getattr(exc, "reason", None)
                timeout_error = isinstance(exc, (socket.timeout, TimeoutError)) or isinstance(
                    reason, (socket.timeout, TimeoutError)
                )
                if time.monotonic() >= deadline or timeout_error:
                    raise ZabbixError("zabbix_timeout") from None
                try:
                    self._check_cancelled(cancelled)
                except ZabbixError:
                    raise
                raise ZabbixError("zabbix_network_unavailable") from None
        finally:
            _ACTIVE_HTTP_DEADLINE.reset(deadline_token)
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
