"""R111: total body-read deadline for Zabbix HTTPS responses.

Synthetic transports only; no real token or network is used.
Author: Abdelhalim Talbi.
"""
import io
import socket
import threading
import time
import unittest
from unittest.mock import patch

from zabbix_readonly import (
    MAX_RESPONSE_BYTES,
    ZabbixError,
    ZabbixReadOnly,
    _read_response_bounded,
)


ORIGIN = "https://zabbix.example.test/zabbix"
TOKEN = "R111_FAKE_TOKEN_MUST_NOT_APPEAR_IN_ERRORS"


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class ChunkedResponse:
    status = 200
    headers = {"Content-Length": "6"}

    def __init__(self, chunks, clock, delay=0.0, *, socket_layer=None):
        self.chunks = list(chunks)
        self.clock = clock
        self.delay = delay
        self.calls = 0
        self.fp = self
        if socket_layer is not None:
            self.raw = socket_layer

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read1(self, amount):
        self.calls += 1
        if self.delay:
            self.clock.advance(self.delay)
        if not self.chunks:
            return b""
        chunk = self.chunks.pop(0)
        if len(chunk) > amount:
            self.chunks.insert(0, chunk[amount:])
            chunk = chunk[:amount]
        return chunk


class FakeSocket:
    def __init__(self):
        self.timeouts = []

    def settimeout(self, seconds):
        self.timeouts.append(seconds)

    def recv(self, _size):
        return b""


class SocketLayer:
    def __init__(self, sock):
        self._sock = sock


class Opener:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return self.response


class SocketBackedResponse:
    status = 200
    headers = {}

    def __init__(self, sock):
        self.fp = self
        self.raw = sock
        self._reader = sock.makefile("rb")
        self.calls = 0

    def read1(self, amount):
        self.calls += 1
        return self._reader.read1(amount)

    def close(self):
        self._reader.close()


class ZabbixResponseDeadlineR111Tests(unittest.TestCase):
    def test_real_socket_slow_trickle_is_stopped_by_absolute_deadline(self):
        client_sock, server_sock = socket.socketpair()
        response = SocketBackedResponse(client_sock)
        stop = threading.Event()

        def drip_bytes():
            try:
                while not stop.is_set():
                    server_sock.sendall(b"x")
                    time.sleep(0.04)
            except OSError:
                pass
            finally:
                try:
                    server_sock.close()
                except OSError:
                    pass

        sender = threading.Thread(target=drip_bytes, daemon=True)
        sender.start()
        started = time.monotonic()
        try:
            with self.assertRaisesRegex(ZabbixError, "^zabbix_timeout$"):
                _read_response_bounded(response, 0.35)
            elapsed = time.monotonic() - started
            self.assertGreaterEqual(response.calls, 2, "test must observe multiple body chunks")
            self.assertGreater(elapsed, 0.20)
            self.assertLess(elapsed, 1.5, "a slow-drip body must not extend the deadline")
        finally:
            stop.set()
            response.close()
            try:
                client_sock.close()
            except OSError:
                pass
            sender.join(timeout=1.0)

    def test_streams_available_chunks_under_deadline(self):
        clock = FakeClock()
        response = ChunkedResponse([b"abc", b"def"], clock, delay=0.1)
        self.assertEqual(_read_response_bounded(response, 1.0, clock=clock), b"abcdef")
        self.assertEqual(response.calls, 3)  # two chunks and EOF

    def test_slow_trickle_cannot_extend_body_deadline(self):
        clock = FakeClock()
        response = ChunkedResponse([b"a", b"b", b"c"], clock, delay=0.2)
        with self.assertRaisesRegex(ZabbixError, "^zabbix_timeout$"):
            _read_response_bounded(response, 0.25, clock=clock)
        self.assertEqual(response.calls, 2)
        self.assertLess(clock(), 1.0)

    def test_cancellation_is_checked_between_chunks(self):
        clock = FakeClock()
        response = ChunkedResponse([b"first", b"second"], clock, delay=0.1)
        with self.assertRaisesRegex(ZabbixError, "^zabbix_request_cancelled$"):
            _read_response_bounded(
                response, 1.0, cancelled=lambda: response.calls > 0, clock=clock
            )
        self.assertEqual(response.calls, 1)

    def test_response_size_limit_is_enforced_while_streaming(self):
        response = io.BytesIO(b"x" * (MAX_RESPONSE_BYTES + 1))
        with self.assertRaisesRegex(ZabbixError, "^zabbix_response_too_large$"):
            _read_response_bounded(response, 5.0, clock=lambda: 0.0)

    def test_remaining_deadline_is_applied_to_underlying_socket(self):
        clock = FakeClock()
        sock = FakeSocket()
        response = ChunkedResponse([b"ok"], clock, delay=0.1,
                                   socket_layer=SocketLayer(sock))
        self.assertEqual(_read_response_bounded(response, 1.0, clock=clock), b"ok")
        self.assertEqual(len(sock.timeouts), 2)
        self.assertAlmostEqual(sock.timeouts[0], 1.0)
        self.assertAlmostEqual(sock.timeouts[1], 0.9)

    def test_socket_timeout_maps_to_neutral_code(self):
        class TimedOut:
            def read1(self, _amount):
                raise TimeoutError("sensitive internal detail")
        with self.assertRaisesRegex(ZabbixError, "^zabbix_timeout$") as caught:
            _read_response_bounded(TimedOut(), 1.0, clock=lambda: 0.0)
        self.assertNotIn("sensitive", str(caught.exception))

    def test_client_does_not_echo_token_when_deadline_expires(self):
        response = ChunkedResponse([], FakeClock())
        response.headers = {"Content-Length": "0"}
        opener = Opener(response)
        client = ZabbixReadOnly(ORIGIN, opener=opener, timeout=1.0)
        with patch("zabbix_readonly._read_response_bounded",
                   side_effect=ZabbixError("zabbix_timeout")):
            with self.assertRaisesRegex(ZabbixError, "^zabbix_timeout$") as caught:
                client.problems(online=True, token=TOKEN)
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(opener.requests[0][0].get_header("Authorization"),
                         "Bearer " + TOKEN)


if __name__ == "__main__":
    unittest.main()
