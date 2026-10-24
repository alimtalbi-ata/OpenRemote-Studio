"""R79: concurrent tunnel close barrier and late SSH channel quarantine.

All network sockets are local; SSH channels are simulated, not OpenSSH live.
Author: Abdelhalim Talbi.
"""
import socket
import threading
import unittest

from remote_tools import Tunnel
from test_tunnel_revocation_r78 import FakeClient, free_port, wait_for


class TunnelCloseBarrierR79(unittest.TestCase):
    def _run_two_closers(self, tunnel, teardown_method, *, started):
        entered = threading.Event()
        release = threading.Event()
        original = getattr(tunnel.server, teardown_method)
        errors = []
        first_done = threading.Event()
        second_done = threading.Event()

        def blocked_teardown():
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test teardown was not released')
            return original()

        setattr(tunnel.server, teardown_method, blocked_teardown)

        def closer(done):
            try:
                tunnel.close()
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                done.set()

        first = threading.Thread(target=closer, args=(first_done,), daemon=True)
        second = threading.Thread(target=closer, args=(second_done,), daemon=True)
        try:
            if started:
                tunnel.start()
            first.start()
            self.assertTrue(entered.wait(2), 'first closer did not reach teardown')
            second.start()
            self.assertFalse(second_done.wait(.15), 'second closer returned before port teardown')
        finally:
            release.set()
            first.join(4)
            second.join(4)
            tunnel.close()
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(errors, [])

    def test_concurrent_close_waits_for_started_listener_shutdown(self):
        port = free_port()
        tunnel = Tunnel(FakeClient(), '127.0.0.1', port, '127.0.0.1', 22)
        self._run_two_closers(tunnel, 'shutdown', started=True)
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', port))

    def test_concurrent_close_before_start_waits_for_port_release(self):
        port = free_port()
        tunnel = Tunnel(FakeClient(), '127.0.0.1', port, '127.0.0.1', 22)
        self._run_two_closers(tunnel, 'server_close', started=False)
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', port))

    def test_start_failure_wakes_concurrent_close_after_teardown(self):
        port = free_port()
        tunnel = Tunnel(FakeClient(), '127.0.0.1', port, '127.0.0.1', 22)
        entered = threading.Event()
        release = threading.Event()
        done = threading.Event()
        original = tunnel.server.server_close
        tunnel.thread.start = lambda: (_ for _ in ()).throw(RuntimeError('thread start refused'))

        def slow_close():
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test did not release teardown')
            original()

        tunnel.server.server_close = slow_close
        failures = []

        def fail_start():
            try:
                tunnel.start()
            except RuntimeError:
                failures.append('start failed')

        starter = threading.Thread(target=fail_start, daemon=True)
        closer = threading.Thread(target=lambda: (tunnel.close(), done.set()), daemon=True)
        try:
            starter.start()
            self.assertTrue(entered.wait(2))
            closer.start()
            self.assertFalse(done.wait(.15), 'close returned before failed-start teardown')
        finally:
            release.set()
            starter.join(4)
            closer.join(4)
        self.assertEqual(failures, ['start failed'])
        self.assertTrue(done.is_set())
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', port))

    def test_late_channel_after_close_is_never_adopted(self):
        port = free_port()
        client = FakeClient()
        entered = threading.Event()
        release = threading.Event()
        created = []

        def delayed_open(kind, destination, origin, timeout=None):
            self.assertEqual(kind, 'direct-tcpip')
            self.assertEqual(timeout, 10)
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test did not release open_channel')
            channel, peer = socket.socketpair()
            created.append((channel, peer))
            return channel

        client.transport.open_channel = delayed_open
        tunnel = Tunnel(client, '127.0.0.1', port, '127.0.0.1', 22)
        tunnel.start()
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=3):
                self.assertTrue(entered.wait(2))
                tunnel.close()
                release.set()
                self.assertTrue(wait_for(lambda: tunnel.active_connections == 0))
                self.assertEqual(len(created), 1)
                self.assertEqual(created[0][0].fileno(), -1,
                                 'late channel was not closed after revocation')
        finally:
            release.set()
            tunnel.close()
            for _, peer in created:
                peer.close()


if __name__ == '__main__':
    unittest.main()
