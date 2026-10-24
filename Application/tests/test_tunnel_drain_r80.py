"""R80: deterministic drain of pending SSH opens (local sockets, fake channels).

Author: Abdelhalim Talbi. No remote SSH server used by these unit tests.
"""
import socket
import threading
import time
import unittest

from remote_tools import Tunnel
from test_tunnel_revocation_r78 import FakeClient, free_port, wait_for


class TunnelDrainR80(unittest.TestCase):
    def test_blocked_open_survives_close_but_drain_times_out_until_release(self):
        client = FakeClient()
        entered, release = threading.Event(), threading.Event()
        created = []
        def slow_open(*args, **kwargs):
            self.assertEqual(kwargs['timeout'], 10)
            entered.set()
            if not release.wait(4):
                raise TimeoutError('fixture open blocked')
            channel, peer = socket.socketpair()
            created.append((channel, peer))
            return channel
        client.transport.open_channel = slow_open
        tunnel = Tunnel(client, '127.0.0.1', free_port(), '127.0.0.1', 22)
        tunnel.start()
        try:
            with socket.create_connection(tunnel.server.server_address, timeout=2):
                self.assertTrue(entered.wait(2))
                self.assertEqual(tunnel.pending_channel_opens, 1)
                tunnel.close()
                self.assertFalse(tunnel.wait_drained(.05))
                self.assertEqual(tunnel.pending_channel_opens, 1)
                release.set()
                self.assertTrue(tunnel.wait_drained(3))
                self.assertEqual(tunnel.pending_channel_opens, 0)
                self.assertEqual(tunnel.active_connections, 0)
                self.assertEqual(len(created), 1)
                self.assertEqual(created[0][0].fileno(), -1)
                self.assertTrue(tunnel.wait_drained(0))
        finally:
            release.set()
            tunnel.close()
            for _, peer in created:
                peer.close()

    def test_multiple_pending_opens_are_bounded_and_all_drained(self):
        client = FakeClient()
        release = threading.Event()
        entered = threading.Event()
        guard = threading.Lock()
        started = [0]
        def slow_open(*args, **kwargs):
            with guard:
                started[0] += 1
                if started[0] == 2:
                    entered.set()
            if not release.wait(4):
                raise TimeoutError('fixture timeout')
            raise OSError('synthetic SSH failure')
        client.transport.open_channel = slow_open
        tunnel = Tunnel(client, '127.0.0.1', free_port(), '127.0.0.1', 22,
                        max_connections=2)
        tunnel.start()
        peers = []
        try:
            for _ in range(2):
                peers.append(socket.create_connection(tunnel.server.server_address, timeout=2))
            self.assertTrue(entered.wait(2))
            self.assertEqual(tunnel.pending_channel_opens, 2)
            self.assertEqual(tunnel.active_connections, 2)
            peers.append(socket.create_connection(tunnel.server.server_address, timeout=2))
            self.assertTrue(wait_for(lambda: tunnel.pending_channel_opens == 2))
            tunnel.close()
            self.assertFalse(tunnel.wait_drained(.05))
            release.set()
            self.assertTrue(tunnel.wait_drained(3))
            self.assertEqual(tunnel.pending_channel_opens, 0)
            self.assertEqual(tunnel.active_connections, 0)
            self.assertEqual(started[0], 2)
        finally:
            release.set()
            tunnel.close()
            for peer in peers:
                peer.close()

    def test_unblocked_open_exception_releases_pending_counter(self):
        client = FakeClient()
        client.transport.fail_open = True
        tunnel = Tunnel(client, '127.0.0.1', free_port(), '127.0.0.1', 22)
        tunnel.start()
        try:
            with socket.create_connection(tunnel.server.server_address, timeout=2):
                self.assertTrue(wait_for(lambda: tunnel.active_connections == 0))
            tunnel.close()
            self.assertTrue(tunnel.wait_drained(1))
            self.assertEqual(tunnel.pending_channel_opens, 0)
        finally:
            tunnel.close()

    def test_drain_waits_for_channel_close_not_just_handler_removal(self):
        client = FakeClient()
        close_entered, release = threading.Event(), threading.Event()
        raw, remote = socket.socketpair()

        class SlowChannel:
            def fileno(self):
                return raw.fileno()
            def recv(self, size):
                return raw.recv(size)
            def sendall(self, data):
                return raw.sendall(data)
            def close(self):
                close_entered.set()
                if not release.wait(4):
                    raise TimeoutError('fixture channel close stalled')
                raw.close()

        client.transport.open_channel = lambda *args, **kwargs: SlowChannel()
        tunnel = Tunnel(client, '127.0.0.1', free_port(), '127.0.0.1', 22)
        tunnel.start()
        closer = None
        try:
            peer = socket.create_connection(tunnel.server.server_address, timeout=2)
            self.assertTrue(wait_for(lambda: tunnel.active_connections == 1
                                     and tunnel.pending_channel_opens == 0))
            peer.close()  # Handler begins channel.close() and blocks.
            self.assertTrue(close_entered.wait(2))
            closer = threading.Thread(target=tunnel.close, daemon=True)
            closer.start()
            self.assertTrue(wait_for(lambda: tunnel._closed))
            self.assertFalse(tunnel.wait_drained(.05),
                             'drain must not finish before SSH channel.close returns')
        finally:
            release.set()
            if closer is not None:
                closer.join(4)
            tunnel.close()
            raw.close()
            remote.close()
        self.assertTrue(tunnel.wait_drained(1))
        self.assertEqual(tunnel.active_connections, 0)

    def test_wait_requires_close_and_bounded_numeric_timeout(self):
        tunnel = Tunnel(FakeClient(), '127.0.0.1', free_port(), '127.0.0.1', 22)
        try:
            with self.assertRaises(RuntimeError):
                tunnel.wait_drained(0)
            for invalid in (True, False, None, -1, float('nan'), float('inf'), 121, '1'):
                with self.subTest(invalid=repr(invalid)):
                    with self.assertRaises(ValueError):
                        tunnel.wait_drained(invalid)
            tunnel.close()
            self.assertTrue(tunnel.wait_drained(0))
        finally:
            tunnel.close()


if __name__ == '__main__':
    unittest.main()
