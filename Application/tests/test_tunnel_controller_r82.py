"""R82 lifecycle: real local sockets, injected fake SSH transport.
No production SSH, external network or secrets. Author: Abdelhalim Talbi.
"""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from ssh_transport import SSHSettings
from tunnel_controller import TunnelController
from test_tunnel_revocation_r78 import FakeClient, free_port
from remote_tools import Tunnel


class R82ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key=Path(self.tmp.name)/'key'
        self.key.write_text('fake fixture key, not used for authentication')
        self.settings=SSHSettings('example.test','operator',22)
        self.local_port=free_port()
        self.params=dict(key_filename=str(self.key), local_port=self.local_port,
                         target_host='127.0.0.1', target_port=22)

    def until(self, fn, timeout=4):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if fn():return
            time.sleep(.02)
        self.fail('state transition timed out')

    def test_offline_default_and_strict_validation_before_network(self):
        calls=[]
        c=TunnelController(connector=lambda *a,**k: calls.append(1))
        self.assertEqual(c.poll().phase,'idle')
        with self.assertRaises(ValueError):c.start(self.settings, **dict(self.params, local_port=0))
        with self.assertRaises(ValueError):c.start(self.settings, **dict(self.params, target_host='bad\nname'))
        with self.assertRaises(ValueError):c.start(self.settings, **dict(self.params, key_filename=''))
        self.assertEqual(c.poll().phase,'idle')
        self.assertEqual(calls,[])
        c.stop();self.until(c.is_shutdown_complete)
        self.assertEqual(c.poll().phase,'closed')

    def test_active_local_tunnel_revocation_releases_port(self):
        import socket
        c=TunnelController(connector=lambda *a,**k: FakeClient())
        c.start(self.settings,**self.params)
        self.until(lambda:c.poll().phase=='active')
        self.assertEqual(c.poll().active_connections,0)
        with socket.create_connection(('127.0.0.1',self.local_port),timeout=3) as peer:
            peer.settimeout(3)
            peer.sendall(b'r82-echo')
            self.assertEqual(peer.recv(8),b'r82-echo')
            c.stop();c.stop()
            self.until(c.is_shutdown_complete)
            try:self.assertEqual(peer.recv(1),b'')
            except (ConnectionResetError,OSError):pass
        self.assertEqual(c.poll().phase,'closed')
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            probe.bind(('127.0.0.1',self.local_port))

    def test_cancel_during_blocked_connect_releases_late_client(self):
        entered,release=threading.Event(),threading.Event()
        clients=[]
        class Client:
            closed=False
            def close(self):self.closed=True
        def connector(*args,**kwargs):
            entered.set()
            self.assertTrue(release.wait(3))
            client=Client();clients.append(client);return client
        c=TunnelController(connector=connector)
        c.start(self.settings,**self.params)
        self.assertTrue(entered.wait(2))
        c.stop()
        self.assertEqual(c.poll().phase,'closing')
        self.assertFalse(c.is_shutdown_complete())
        release.set()
        self.until(c.is_shutdown_complete)
        self.assertEqual(c.poll().phase,'closed')
        self.assertTrue(clients[0].closed)

    def test_connect_failure_is_redacted_and_does_not_leak_target(self):
        def connector(*args,**kwargs):
            raise RuntimeError('private path /home/secret, target=example.test')
        c=TunnelController(connector=connector)
        c.start(self.settings,**self.params)
        self.until(c.is_shutdown_complete)
        self.assertEqual(c.poll().phase,'failed')
        self.assertNotIn('secret',str(c.poll()))
        self.assertNotIn('example.test',str(c.poll()))

    def test_cancel_during_tunnel_creation_before_start(self):
        entered,release=threading.Event(),threading.Event()
        created=[]
        def tunnel_factory(*args):
            entered.set();self.assertTrue(release.wait(3))
            tunnel=Tunnel(*args);created.append(tunnel);return tunnel
        c=TunnelController(connector=lambda *a,**k:FakeClient(),
                           tunnel_factory=tunnel_factory)
        c.start(self.settings,**self.params)
        self.assertTrue(entered.wait(2))
        c.stop()
        self.assertFalse(c.is_shutdown_complete())
        release.set()
        self.until(c.is_shutdown_complete)
        self.assertEqual(c.poll().phase,'closed')
        self.assertEqual(len(created),1)
        import socket
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',self.local_port))

    def test_controller_is_one_shot_even_after_stop(self):
        c=TunnelController()
        c.stop()
        with self.assertRaises(RuntimeError):c.start(self.settings,**self.params)


if __name__=='__main__':unittest.main()
