"""R81: loopback listener teardown and nonblocking GUI status contracts.

Author: Abdelhalim Talbi. SSH channels are simulated; no production SSH.
"""
from pathlib import Path
import threading
import unittest

from remote_tools import Tunnel
from tunnel_shutdown_status import TunnelShutdownStatus
from test_tunnel_revocation_r78 import FakeClient, free_port


class ScopeFixture:
    def __init__(self):
        self.closed = False
        self.cleaned = False
        self.calls = []

    def wait_closed(self, timeout):
        self.calls.append(timeout)
        assert timeout == 0, 'GUI status must never block'
        return self.cleaned


class TunnelFixture:
    def __init__(self):
        self.drained = False
        self.calls = []

    def wait_drained(self, timeout):
        self.calls.append(timeout)
        assert timeout == 0, 'GUI status must never block'
        return self.drained


class TunnelShutdownR81(unittest.TestCase):
    def test_wait_drained_cannot_precede_listener_teardown(self):
        tunnel = Tunnel(FakeClient(), '127.0.0.1', free_port(), '127.0.0.1', 22)
        tunnel.start()
        entered, release = threading.Event(), threading.Event()
        original = tunnel.server.server_close

        def delayed_server_close():
            entered.set()
            if not release.wait(4):
                raise TimeoutError('fixture close blocked')
            original()

        tunnel.server.server_close = delayed_server_close
        closer = threading.Thread(target=tunnel.close, daemon=True)
        try:
            closer.start()
            self.assertTrue(entered.wait(3), 'close never reached server_close')
            self.assertEqual(tunnel.active_connections, 0)
            self.assertEqual(tunnel.pending_channel_opens, 0)
            self.assertFalse(tunnel.wait_drained(.05),
                             'no handlers does not mean listener teardown finished')
            release.set()
            closer.join(4)
            self.assertFalse(closer.is_alive())
            self.assertTrue(tunnel.wait_drained(1))
        finally:
            release.set()
            closer.join(4)
            tunnel.close()

    def test_poll_progression_is_nonblocking_and_has_no_endpoint_details(self):
        scope, tunnel = ScopeFixture(), TunnelFixture()
        observer = TunnelShutdownStatus(scope, tunnel)
        self.assertEqual(observer.poll(), 'open')
        self.assertEqual(scope.calls, [])
        scope.closed = True
        self.assertEqual(observer.poll(), 'cleanup')
        self.assertEqual(tunnel.calls, [])
        scope.cleaned = True
        self.assertEqual(observer.poll(), 'draining')
        tunnel.drained = True
        self.assertEqual(observer.poll(), 'complete')
        self.assertEqual(scope.calls, [0, 0, 0])
        self.assertEqual(tunnel.calls, [0, 0])

    def test_poll_without_tunnel_waits_for_scope_only(self):
        scope = ScopeFixture()
        scope.closed = True
        status = TunnelShutdownStatus(scope)
        self.assertEqual(status.poll(), 'cleanup')
        scope.cleaned = True
        self.assertEqual(status.poll(), 'complete')

    def test_tk_tunnel_shutdown_keeps_event_loop_responsive(self):
        code = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
        body = code.split('    def tunnel_dialog(self):', 1)[1].split('    def network_tool(self,kind):', 1)[0]
        self.assertIn("state['startup_done'].is_set()", body)
        self.assertIn("TunnelShutdownStatus(scope,state['tunnel']).poll()", body)
        self.assertIn('win.after(100,check_shutdown)', body)
        self.assertIn('win.after(1000,check_shutdown)', body)
        self.assertNotIn('scope.wait_closed(10)', body)
        self.assertNotIn('tunnel.wait_drained(10)', body)


if __name__ == '__main__':
    unittest.main()
