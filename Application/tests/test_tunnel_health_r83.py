"""R83: real loopback listener, simulated SSH link loss, no external traffic.
Author: Abdelhalim Talbi.
"""
import socket
import tempfile
import time
import unittest
from pathlib import Path
from ssh_transport import SSHSettings
from tunnel_controller import TunnelController
from test_tunnel_revocation_r78 import FakeClient, free_port


class LinkClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.transport = self.get_transport()

    def get_transport(self):
        return self.transport if hasattr(self, 'transport') else super().get_transport()


class R83TunnelHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.key = Path(self.temp.name) / 'key'
        self.key.write_text('synthetic test fixture, not a private key')
        self.port = free_port()
        self.settings = SSHSettings('example.test', 'operator', 22)
        self.args = dict(key_filename=str(self.key), local_port=self.port,
                         target_host='127.0.0.1', target_port=22)

    def until(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.02)
        self.fail('timeout waiting for tunnel transition')

    def test_ssh_disconnect_revokes_listener_and_reports_sanitized_state(self):
        client = LinkClient()
        c = TunnelController(connector=lambda *a, **kw: client)
        c.start(self.settings, **self.args)
        self.until(lambda: c.poll().phase == 'active')
        client.transport.is_active = lambda: False
        self.until(lambda: c.poll().phase == 'disconnected')
        self.assertTrue(c.is_shutdown_complete())
        self.assertNotIn('example.test', str(c.poll()))
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', self.port))
        c.stop()
        self.assertEqual(c.poll().phase, 'disconnected')

    def test_transport_health_exception_fails_closed_without_secret(self):
        client = LinkClient()
        c = TunnelController(connector=lambda *a, **kw: client)
        c.start(self.settings, **self.args)
        self.until(lambda: c.poll().phase == 'active')
        def broken():
            raise RuntimeError('secret key path and remote endpoint')
        client.transport.is_active = broken
        self.until(lambda: c.poll().phase == 'disconnected')
        self.assertNotIn('secret', str(c.poll()))
        self.assertTrue(c.is_shutdown_complete())

    def test_stable_transport_remains_active_until_explicit_stop(self):
        c = TunnelController(connector=lambda *a, **kw: LinkClient())
        c.start(self.settings, **self.args)
        self.until(lambda: c.poll().phase == 'active')
        self.assertEqual(c.poll().phase, 'active')
        c.stop()
        self.until(c.is_shutdown_complete)
        self.assertEqual(c.poll().phase, 'closed')

    def test_disconnect_during_concurrent_stop_does_not_reopen(self):
        client = LinkClient()
        c = TunnelController(connector=lambda *a, **kw: client)
        c.start(self.settings, **self.args)
        self.until(lambda: c.poll().phase == 'active')
        client.transport.is_active = lambda: False
        c.stop()
        self.until(c.is_shutdown_complete)
        self.assertIn(c.poll().phase, ('closed', 'disconnected'))
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', self.port))


if __name__ == '__main__':
    unittest.main()
