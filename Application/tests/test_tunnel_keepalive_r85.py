"""R85 opt-in SSH keepalive; local fakes only. Author: Abdelhalim Talbi."""
import tempfile
import time
import unittest
from pathlib import Path
from ssh_transport import SSHSettings
from tunnel_controller import TunnelController
from test_tunnel_health_r83 import LinkClient
from test_tunnel_revocation_r78 import free_port

class KeepaliveTests(unittest.TestCase):
    def test_invalid_interval_rejected_before_connector(self):
        called = []
        c = TunnelController(connector=lambda *a, **kw: called.append(1))
        for bad in (-1, 301, True, 2.5, '15', None):
            with self.assertRaises(ValueError):
                c.start(SSHSettings('example.test', 'user'), key_filename='not-a-key',
                        local_port=12345, target_host='127.0.0.1', target_port=22,
                        keepalive_seconds=bad)
        self.assertEqual(called, [])

    def test_keepalive_configured_before_listener(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d)/'fixture'; key.write_text('synthetic')
            client = LinkClient()
            calls = []
            client.transport.set_keepalive = lambda seconds: calls.append(seconds)
            c = TunnelController(connector=lambda *a, **kw: client)
            c.start(SSHSettings('example.test','user'), key_filename=str(key),
                    local_port=free_port(), target_host='127.0.0.1', target_port=22,
                    keepalive_seconds=15)
            try:
                deadline=time.monotonic()+4
                while not calls and time.monotonic()<deadline: time.sleep(.01)
                self.assertEqual(calls,[15])
            finally: c.stop()

    def test_missing_keepalive_api_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            key=Path(d)/'fixture'; key.write_text('synthetic')
            client=LinkClient()
            c=TunnelController(connector=lambda *a, **kw: client)
            c.start(SSHSettings('example.test','user'), key_filename=str(key),
                    local_port=free_port(), target_host='127.0.0.1', target_port=22,
                    keepalive_seconds=15)
            deadline=time.monotonic()+4
            while not c._startup_done.is_set() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(c._scope.cancelled)
            self.assertNotEqual(c.poll().phase,'active')
            c.stop()

if __name__=='__main__': unittest.main()
