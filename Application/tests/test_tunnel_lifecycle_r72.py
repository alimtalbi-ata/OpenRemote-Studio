"""R72: real local TCP forwarding and cancellation lifecycle, no SSH server."""
import socket
import threading
import unittest

from remote_tools import Tunnel


class EchoTransport:
    def __init__(self):
        self.opened = 0

    def is_active(self):
        return True

    def open_channel(self, kind, destination, origin, timeout=None):
        assert kind == 'direct-tcpip'
        self.opened += 1
        local, peer = socket.socketpair()

        def echo():
            with peer:
                while True:
                    try:
                        data = peer.recv(32768)
                        if not data:
                            break
                        peer.sendall(data)
                    except OSError:
                        break

        threading.Thread(target=echo, daemon=True).start()
        return local


class FakeClient:
    def __init__(self):
        self.transport = EchoTransport()

    def get_transport(self):
        return self.transport


def unused_port(family=socket.AF_INET, host='127.0.0.1'):
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


class TunnelLifecycleR72(unittest.TestCase):
    def test_close_before_start_releases_reserved_port(self):
        port = unused_port()
        tunnel = Tunnel(FakeClient(), '127.0.0.1', port, 'internal.example', 443)
        # Would deadlock indefinitely in the previous implementation.
        done = threading.Event()
        worker = threading.Thread(target=lambda: (tunnel.close(), done.set()), daemon=True)
        worker.start()
        self.assertTrue(done.wait(2), 'close() blocked without serve_forever()')
        tunnel.close()  # Idempotent.
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', port))
        with self.assertRaises(RuntimeError):
            tunnel.start()

    def test_live_loopback_forward_and_cleanup(self):
        port = unused_port()
        client = FakeClient()
        tunnel = Tunnel(client, 'localhost', port, 'internal.example', 443)
        try:
            tunnel.start()
            with socket.create_connection(('127.0.0.1', port), timeout=3) as sock:
                sock.settimeout(3)
                sock.sendall(b'R72-echo')
                self.assertEqual(sock.recv(64), b'R72-echo')
            self.assertEqual(client.transport.opened, 1)
            with self.assertRaises(RuntimeError):
                tunnel.start()
        finally:
            tunnel.close()
            tunnel.close()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', port))

    def test_invalid_public_bind_and_target_are_rejected(self):
        for host in ('0.0.0.0', '::', '192.0.2.10'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                Tunnel(FakeClient(), host, 23456, 'internal.example', 443)
        for target in ('', 'host\nInjected', 'bad host', '\x00'):
            with self.subTest(target=repr(target)), self.assertRaises(ValueError):
                Tunnel(FakeClient(), '127.0.0.1', 23456, target, 443)
        with self.assertRaises(ValueError):
            Tunnel(FakeClient(), '127.0.0.1', True, 'internal.example', 443)

    def test_ipv6_loopback_when_available(self):
        if not socket.has_ipv6:
            self.skipTest('IPv6 not available')
        try:
            port = unused_port(socket.AF_INET6, '::1')
        except OSError:
            self.skipTest('IPv6 loopback not bound on this runner')
        tunnel = Tunnel(FakeClient(), '::1', port, 'internal.example', 443)
        try:
            tunnel.start()
            with socket.create_connection(('::1', port), timeout=3) as sock:
                sock.settimeout(3)
                sock.sendall(b'ipv6')
                self.assertEqual(sock.recv(16), b'ipv6')
        finally:
            tunnel.close()

    def test_closed_ssh_transport_is_rejected(self):
        client = FakeClient()
        client.transport.is_active = lambda: False
        with self.assertRaises(RuntimeError):
            Tunnel(client, '127.0.0.1', unused_port(), 'internal.example', 443)


if __name__ == '__main__':
    unittest.main()
