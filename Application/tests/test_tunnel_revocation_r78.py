"""R78 loopback TCP tests: real sockets, fake SSH channels (NOT live OpenSSH)."""
import socket
import threading
import time
import unittest

from remote_tools import Tunnel


class FakeTransport:
    def __init__(self):
        self.active = True
        self.channels = []
        self.lock = threading.Lock()
        self.fail_open = False

    def is_active(self):
        return self.active

    def open_channel(self, kind, destination, origin, timeout=None):
        assert kind == 'direct-tcpip'
        assert timeout is not None and timeout <= 10
        if self.fail_open:
            raise OSError('secret-token-should-not-be-logged')
        client, server = socket.socketpair()
        with self.lock:
            self.channels.append(client)

        def echo():
            with server:
                while True:
                    try:
                        data = server.recv(32768)
                        if not data:
                            break
                        server.sendall(data)
                    except OSError:
                        break
        threading.Thread(target=echo, daemon=True).start()
        return client


class FakeClient:
    def __init__(self):
        self.transport = FakeTransport()

    def get_transport(self):
        return self.transport


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for(predicate, seconds=3):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(.02)
    return predicate()


class TunnelRevocationR78(unittest.TestCase):
    def test_close_revokes_existing_forwarding_and_releases_port(self):
        port = free_port()
        client = FakeClient()
        tunnel = Tunnel(client, 'localhost', port, '127.0.0.1', 22)
        tunnel.start()
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=3) as sock:
                sock.settimeout(3)
                sock.sendall(b'hello')
                self.assertEqual(sock.recv(5), b'hello')
                self.assertTrue(wait_for(lambda: tunnel.active_connections == 1))
                channel = client.transport.channels[0]
                tunnel.close()
                self.assertEqual(tunnel.active_connections, 0)
                self.assertEqual(channel.fileno(), -1)
                try:
                    self.assertEqual(sock.recv(5), b'')
                except (ConnectionResetError, OSError):
                    pass  # TCP reset is a valid explicit revocation.
        finally:
            tunnel.close()
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', port))

    def test_bounded_active_connections_and_recovery(self):
        port = free_port()
        client = FakeClient()
        tunnel = Tunnel(client, '127.0.0.1', port, '127.0.0.1', 22, max_connections=1)
        tunnel.start()
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=3) as first:
                first.settimeout(3)
                first.sendall(b'one')
                self.assertEqual(first.recv(3), b'one')
                with socket.create_connection(('127.0.0.1', port), timeout=3) as second:
                    second.settimeout(3)
                    try:
                        self.assertEqual(second.recv(1), b'')
                    except ConnectionResetError:
                        pass
                self.assertEqual(len(client.transport.channels), 1)
            self.assertTrue(wait_for(lambda: tunnel.active_connections == 0))
            with socket.create_connection(('127.0.0.1', port), timeout=3) as third:
                third.settimeout(3)
                third.sendall(b'two')
                self.assertEqual(third.recv(3), b'two')
                self.assertEqual(len(client.transport.channels), 2)
        finally:
            tunnel.close()

    def test_disconnected_transport_does_not_open_channel(self):
        port = free_port()
        client = FakeClient()
        tunnel = Tunnel(client, '127.0.0.1', port, '127.0.0.1', 22)
        tunnel.start()
        try:
            client.transport.active = False
            with socket.create_connection(('127.0.0.1', port), timeout=3) as sock:
                sock.settimeout(3)
                try:
                    self.assertEqual(sock.recv(1), b'')
                except ConnectionResetError:
                    pass
            self.assertEqual(client.transport.channels, [])
            self.assertTrue(wait_for(lambda: tunnel.active_connections == 0))
        finally:
            tunnel.close()

    def test_failed_channel_is_closed_without_traceback_or_secret(self):
        port = free_port()
        client = FakeClient()
        client.transport.fail_open = True
        tunnel = Tunnel(client, '127.0.0.1', port, '127.0.0.1', 22)
        tunnel.start()
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=3) as sock:
                sock.settimeout(3)
                try:
                    self.assertEqual(sock.recv(1), b'')
                except ConnectionResetError:
                    pass
            self.assertTrue(wait_for(lambda: tunnel.active_connections == 0))
        finally:
            tunnel.close()

    def test_invalid_limits_rejected_before_bind(self):
        for limit in (0, -1, 65, True, False, 1.0, '16', None):
            with self.subTest(limit=repr(limit)):
                with self.assertRaises(ValueError):
                    Tunnel(FakeClient(), '127.0.0.1', free_port(), '127.0.0.1', 22,
                           max_connections=limit)

    def test_concurrent_close_is_idempotent(self):
        port = free_port()
        tunnel = Tunnel(FakeClient(), '127.0.0.1', port, '127.0.0.1', 22)
        tunnel.start()
        with socket.create_connection(('127.0.0.1', port), timeout=3) as sock:
            sock.settimeout(3)
            sock.sendall(b'x')
            self.assertEqual(sock.recv(1), b'x')
            errors = []
            def closer():
                try:
                    tunnel.close()
                except Exception as exc:
                    errors.append(type(exc).__name__)
            threads = [threading.Thread(target=closer) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(4)
                self.assertFalse(thread.is_alive(), 'close() deadlocked')
            self.assertEqual(errors, [])
            self.assertEqual(tunnel.active_connections, 0)
            with self.assertRaises(RuntimeError):
                tunnel.start()


if __name__ == '__main__':
    unittest.main()
