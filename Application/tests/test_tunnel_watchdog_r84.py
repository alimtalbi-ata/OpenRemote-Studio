"""R84: SSH health watchdog works without Qt polling; local sockets and fake SSH.
No production SSH or external traffic. Author: Abdelhalim Talbi.
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


class R84HeadlessWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key = Path(self.tmp.name) / 'fixture'
        self.key.write_text('synthetic fixture; no real private key')
        self.port = free_port()
        self.settings = SSHSettings('example.test', 'operator', 22)
        self.params = dict(key_filename=str(self.key), local_port=self.port,
                           target_host='127.0.0.1', target_port=22)

    def until(self, condition, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(.02)
        self.fail('watchdog state transition timeout')

    def start_active(self, client):
        controller = TunnelController(connector=lambda *a, **kw: client)
        controller.start(self.settings, **self.params)
        self.until(lambda: controller.poll().phase == 'active')
        self.addCleanup(controller.stop)
        return controller

    def test_link_loss_revoked_without_any_subsequent_poll(self):
        client = LinkClient()
        controller = self.start_active(client)
        client.transport.is_active = lambda: False
        # Deliberately do not call poll() or is_shutdown_complete() here:
        # the independent watchdog must initiate cancellation.
        self.until(lambda: controller._scope.cancelled)
        self.until(controller.is_shutdown_complete)
        self.assertEqual(controller.poll().phase, 'disconnected')
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', self.port))

    def test_health_exception_revokes_without_leaking_exception_text(self):
        client = LinkClient()
        controller = self.start_active(client)
        def broken():
            raise RuntimeError('secret=fixture; remote=example.test')
        client.transport.is_active = broken
        self.until(lambda: controller._scope.cancelled)
        self.until(controller.is_shutdown_complete)
        self.assertEqual(controller.poll().phase, 'disconnected')
        self.assertNotIn('secret', repr(controller.poll()))
        self.assertNotIn('example.test', repr(controller.poll()))

    def test_explicit_stop_terminates_watchdog_and_preserves_closed(self):
        controller = self.start_active(LinkClient())
        watchdog = controller._watchdog
        self.assertIsNotNone(watchdog)
        controller.stop()
        self.until(controller.is_shutdown_complete)
        watchdog.join(timeout=2)
        self.assertFalse(watchdog.is_alive())
        self.assertEqual(controller.poll().phase, 'closed')

    def test_stop_race_cannot_reactivate_after_connecting(self):
        entered = threading.Event()
        release = threading.Event()
        client = LinkClient()
        def connector(*args, **kwargs):
            entered.set()
            if not release.wait(3):
                raise RuntimeError('fixture timeout')
            return client
        controller = TunnelController(connector=connector)
        controller.start(self.settings, **self.params)
        self.assertTrue(entered.wait(2))
        controller.stop()
        release.set()
        self.until(controller.is_shutdown_complete)
        self.assertEqual(controller.poll().phase, 'closed')
        self.assertIsNone(controller._watchdog)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', self.port))

    def test_offline_default_has_no_background_watchdog(self):
        controller = TunnelController()
        self.assertIsNone(controller._watchdog)
        self.assertEqual(controller.poll().phase, 'idle')
        controller.stop()
        self.until(controller.is_shutdown_complete)
        self.assertIsNone(controller._watchdog)


if __name__ == '__main__':
    unittest.main()
