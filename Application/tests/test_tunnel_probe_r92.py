"""R92 bounded SSH reply probe, local TCP sockets and fake SSH transport only.
No production network, no credentials. Author: Abdelhalim Talbi.
"""
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from ssh_transport import SSHSettings
from tunnel_controller import TunnelController
from test_tunnel_health_r83 import LinkClient
from test_tunnel_revocation_r78 import free_port


class R92BoundedProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.key = Path(self.temp.name) / 'synthetic-key'
        self.key.write_text('not a real private key')
        self.port = free_port()
        self.settings = SSHSettings('example.test', 'operator', 22)
        self.kwargs = dict(key_filename=str(self.key), local_port=self.port,
                           target_host='127.0.0.1', target_port=22)

    def until(self, predicate, seconds=6):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if predicate():
                return
            time.sleep(.02)
        self.fail('timeout waiting for synthetic SSH probe transition')

    def start_active(self, client, **options):
        controller = TunnelController(connector=lambda *a, **kw: client)
        controller.start(self.settings, **self.kwargs, **options)
        self.addCleanup(controller.stop)
        self.until(lambda: controller.poll().phase == 'active')
        return controller

    def test_invalid_bounds_rejected_before_network_or_listener(self):
        called = []
        for field, values in (
            ('probe_interval_seconds', (-1, 301, True, 1.5, '15', None)),
            ('probe_timeout_seconds', (0, 31, True, 1.5, '5', None)),
        ):
            for value in values:
                with self.subTest(field=field, value=value):
                    controller = TunnelController(connector=lambda *a, **kw: called.append(1))
                    with self.assertRaises(ValueError):
                        controller.start(self.settings, **self.kwargs, **{field: value})
        self.assertEqual(called, [])
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', self.port))

    def test_disabled_by_default_never_probes(self):
        client = LinkClient()
        called = []
        client.transport.global_request = lambda *a, **kw: called.append(1)
        controller = self.start_active(client)
        time.sleep(1.25)
        self.assertEqual(called, [])
        self.assertEqual(controller.poll().phase, 'active')

    def test_rejected_global_request_reply_counts_as_alive(self):
        client = LinkClient()
        calls = []
        def reply(kind, wait=False):
            calls.append((kind, wait))
            return None  # OpenSSH SSH_MSG_REQUEST_FAILURE is still a reply.
        client.transport.global_request = reply
        controller = self.start_active(client, probe_interval_seconds=1, probe_timeout_seconds=1)
        self.until(lambda: len(calls) >= 2, seconds=5)
        self.assertEqual(controller.poll().phase, 'active')
        self.assertEqual(calls, [('keepalive@openssh.com', True)] * len(calls))

    def test_silent_unanswered_probe_revokes_without_qt_poll(self):
        client = LinkClient()
        entered = threading.Event()
        release = threading.Event()
        calls = []
        def blackhole(kind, wait=False):
            calls.append(1)
            entered.set()
            release.wait(5)  # Simulate a missing reply while is_active stays True.
            return None
        client.transport.global_request = blackhole
        controller = self.start_active(client, probe_interval_seconds=1, probe_timeout_seconds=1)
        try:
            self.assertTrue(entered.wait(3))
            # No poll()/Qt refresh until the watchdog itself has revoked.
            self.until(lambda: controller._scope.cancelled, seconds=4)
            self.until(controller.is_shutdown_complete)
            self.assertEqual(controller.poll().phase, 'disconnected')
            self.assertEqual(len(calls), 1)  # No probe storm on blackhole.
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', self.port))
        finally:
            release.set()

    def test_probe_exception_is_redacted_and_fails_closed(self):
        client = LinkClient()
        def broken(*args, **kwargs):
            raise RuntimeError('private-key=/sensitive; password=fixture')
        client.transport.global_request = broken
        controller = self.start_active(client, probe_interval_seconds=1, probe_timeout_seconds=2)
        self.until(lambda: controller._scope.cancelled)
        self.until(controller.is_shutdown_complete)
        self.assertEqual(controller.poll().phase, 'disconnected')
        self.assertNotIn('private-key', repr(controller.poll()))
        self.assertNotIn('password', repr(controller.poll()))

    def test_manual_stop_while_probe_waits_does_not_change_closed_state(self):
        client = LinkClient()
        entered = threading.Event()
        release = threading.Event()
        def blackhole(*args, **kwargs):
            entered.set()
            release.wait(5)
        client.transport.global_request = blackhole
        controller = self.start_active(client, probe_interval_seconds=1, probe_timeout_seconds=2)
        try:
            self.assertTrue(entered.wait(3))
            controller.stop()
            self.until(controller.is_shutdown_complete)
            release.set()
            self.assertEqual(controller.poll().phase, 'closed')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', self.port))
        finally:
            release.set()


if __name__ == '__main__':
    unittest.main()
