"""R112: one absolute deadline for the complete Zabbix HTTPS transaction.

The slow-header/body tests use real local sockets only; no external service or
real credential is used. TLS verification remains enabled in the production
HTTPS handler. Author: Abdelhalim Talbi.
"""
import http.client
import ipaddress
import socket
import ssl
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import OpenerDirector, build_opener

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from zabbix_readonly import (
    MAX_RESPONSE_BYTES,
    ZabbixError,
    ZabbixReadOnly,
    _ACTIVE_HTTP_DEADLINE,
    _DeadlineHTTPSConnection,
    _DeadlineHTTPSHandler,
    _RejectRedirects,
    _read_response_bounded,
)
from test_zabbix_response_deadline_r111 import ChunkedResponse, FakeClock, ORIGIN, TOKEN


class _ClosableResponse(ChunkedResponse):
    def __init__(self, chunks, clock):
        super().__init__(chunks, clock)
        self.closed = False

    def close(self):
        self.closed = True


class _SlowOpener:
    def __init__(self, response, delay):
        self.response = response
        self.delay = delay
        self.calls = 0

    def __call__(self, _request, timeout):
        self.calls += 1
        self.timeout = timeout
        time.sleep(self.delay)
        return self.response


class ZabbixTransactionDeadlineR112Tests(unittest.TestCase):
    def test_body_uses_original_transaction_deadline_not_a_fresh_budget(self):
        clock = FakeClock()
        response = ChunkedResponse([b"a", b"b", b"c"], clock, delay=0.1)
        with self.assertRaisesRegex(ZabbixError, "^zabbix_timeout$"):
            _read_response_bounded(response, 1.0, deadline=0.25, clock=clock)
        self.assertEqual(response.calls, 3)
        self.assertAlmostEqual(clock(), 0.3)

    def test_opening_that_returns_after_deadline_is_rejected_and_closed(self):
        response = _ClosableResponse([b'{"result":[]}'], FakeClock())
        opener = _SlowOpener(response, delay=0.08)
        client = ZabbixReadOnly(ORIGIN, opener=opener, timeout=0.03)
        started = time.monotonic()
        with self.assertRaisesRegex(ZabbixError, "^zabbix_timeout$") as caught:
            client._call("problem.get", {"output": ["eventid"]}, token=TOKEN)
        self.assertGreaterEqual(time.monotonic() - started, 0.07)
        self.assertTrue(response.closed)
        self.assertEqual(opener.calls, 1)
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_absolute_deadline_interrupts_a_slow_http_status_line(self):
        client_sock, server_sock = socket.socketpair()
        timeout = 0.35
        deadline = time.monotonic() + timeout
        context_token = _ACTIVE_HTTP_DEADLINE.set(deadline)
        try:
            connection = _DeadlineHTTPSConnection(
                "zabbix.invalid", timeout=timeout, context=ssl.create_default_context()
            )
        finally:
            _ACTIVE_HTTP_DEADLINE.reset(context_token)
        connection.sock = client_sock
        server_done = threading.Event()

        def send_slow_status_line():
            try:
                request_file = server_sock.makefile("rb")
                while request_file.readline() not in (b"\r\n", b"\n", b""):
                    pass
                # Each byte arrives faster than the inactivity timeout, but the
                # complete status line cannot arrive before the absolute deadline.
                for byte in b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK":
                    server_sock.sendall(bytes((byte,)))
                    time.sleep(0.025)
            except (OSError, ValueError):
                pass
            finally:
                server_done.set()
                try:
                    server_sock.close()
                except OSError:
                    pass

        sender = threading.Thread(target=send_slow_status_line, daemon=True)
        started = time.monotonic()
        try:
            connection.request("POST", "/api_jsonrpc.php", body=b"{}",
                               headers={"Content-Type": "application/json-rpc"})
            sender.start()
            with self.assertRaises((OSError, http.client.HTTPException)):
                connection.getresponse()
            elapsed = time.monotonic() - started
            self.assertTrue(connection._deadline_expired)
            self.assertGreater(elapsed, 0.20)
            self.assertLess(elapsed, 1.5, "slow headers must not outlive the transaction deadline")
        finally:
            connection.close()
            try:
                server_sock.close()
            except OSError:
                pass
            if sender.ident is not None:
                sender.join(timeout=1.0)
        self.assertTrue(server_done.wait(0.2))

    def test_successful_response_close_cancels_deadline_watchdog(self):
        client_sock, server_sock = socket.socketpair()
        timeout = 1.5
        context_token = _ACTIVE_HTTP_DEADLINE.set(time.monotonic() + timeout)
        try:
            connection = _DeadlineHTTPSConnection(
                "zabbix.invalid", timeout=timeout, context=ssl.create_default_context()
            )
        finally:
            _ACTIVE_HTTP_DEADLINE.reset(context_token)
        connection.sock = client_sock

        def answer_once():
            try:
                request_file = server_sock.makefile("rb")
                while request_file.readline() not in (b"\r\n", b"\n", b""):
                    pass
                server_sock.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK"
                )
            except OSError:
                pass

        sender = threading.Thread(target=answer_once, daemon=True)
        try:
            connection.request("POST", "/api_jsonrpc.php", body=b"{}")
            sender.start()
            response = connection.getresponse()
            self.assertEqual(response.read(2), b"OK")
            response.close()
            self.assertIsNone(connection._deadline_timer)
            self.assertFalse(connection._deadline_expired)
        finally:
            connection.close()
            try:
                server_sock.close()
            except OSError:
                pass
            sender.join(timeout=1.0)

    def test_real_local_tls_slow_headers_are_cut_off_by_transaction_watchdog(self):
        # Generate a throwaway local trust anchor at runtime: no certificate or
        # private key is checked into the repository or copied into the archive.
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject).issuer_name(subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(minutes=10))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]), critical=False)
            .sign(private_key, hashes.SHA256())
        )
        with tempfile.TemporaryDirectory(prefix="openremote-r112-") as temp_dir:
            cert_path = Path(temp_dir) / "ephemeral-test-ca.pem"
            key_path = Path(temp_dir) / "ephemeral-test-key.pem"
            cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
            key_path.write_bytes(private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            ))
            server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server_context.load_cert_chain(str(cert_path), str(key_path))
            client_context = ssl.create_default_context(cafile=str(cert_path))
            self.assertTrue(client_context.check_hostname)
            self.assertEqual(client_context.verify_mode, ssl.CERT_REQUIRED)

            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(2.0)
            port = listener.getsockname()[1]
            server_done = threading.Event()
            request_received = threading.Event()

            def slow_headers():
                connection = None
                request_file = None
                try:
                    raw, _peer = listener.accept()
                    connection = server_context.wrap_socket(raw, server_side=True)
                    connection.settimeout(2.0)
                    request_file = connection.makefile("rb")
                    request_file.readline()
                    content_length = 0
                    while True:
                        line = request_file.readline()
                        if line in (b"\r\n", b"\n", b""):
                            break
                        if line.lower().startswith(b"content-length:"):
                            content_length = int(line.split(b":", 1)[1].strip())
                    request_file.read(content_length)
                    # Prove this is a slow-response test, not a failed connection
                    # caused by name resolution or an address-family mismatch.
                    request_received.set()
                    payload = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}"
                    for byte in payload:
                        connection.sendall(bytes((byte,)))
                        time.sleep(0.025)
                except (OSError, ValueError, ssl.SSLError):
                    pass
                finally:
                    if request_file is not None:
                        try:
                            request_file.close()
                        except OSError:
                            pass
                    if connection is not None:
                        try:
                            connection.close()
                        except OSError:
                            pass
                    server_done.set()

            server_thread = threading.Thread(target=slow_headers, daemon=True)
            server_thread.start()
            opener = build_opener(
                _RejectRedirects(), _DeadlineHTTPSHandler(context=client_context)
            ).open
            # Use a literal IPv4 loopback plus matching certificate SAN. This test
            # isolates the response deadline instead of depending on how the OS
            # orders or maps "localhost" between IPv4 and IPv6.
            client = ZabbixReadOnly(f"https://127.0.0.1:{port}", opener=opener, timeout=0.4)
            started = time.monotonic()
            try:
                with self.assertRaisesRegex(ZabbixError, "^zabbix_timeout$") as caught:
                    client._call("problem.get", {"output": ["eventid"]}, token=TOKEN)
                elapsed = time.monotonic() - started
                self.assertNotIn(TOKEN, str(caught.exception))
                self.assertGreater(elapsed, 0.20)
                self.assertLess(elapsed, 1.5, "TLS/HTTP header trickle must not reset the deadline")
            finally:
                listener.close()
                server_thread.join(timeout=2.0)
            self.assertTrue(request_received.is_set(), "TLS/HTTP request did not reach the slow-header fixture")
            self.assertTrue(server_done.wait(0.2))

    def test_default_opener_keeps_strict_tls_and_redirect_rejection(self):
        client = ZabbixReadOnly(ORIGIN)
        opener = client._opener.__self__
        self.assertIsInstance(opener, OpenerDirector)
        handlers = opener.handlers
        https = next(handler for handler in handlers if isinstance(handler, _DeadlineHTTPSHandler))
        self.assertTrue(https._context.check_hostname)
        self.assertEqual(https._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(any(type(handler).__name__ == "_RejectRedirects" for handler in handlers))

    def test_transaction_deadline_does_not_change_payload_cap(self):
        self.assertEqual(MAX_RESPONSE_BYTES, 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
