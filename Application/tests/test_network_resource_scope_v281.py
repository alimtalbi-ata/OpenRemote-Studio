import threading
import unittest
from network_resource_scope import NetworkResourceScope

class Resource:
    def __init__(self, gate=None):
        self.gate=gate
        self.closed=threading.Event()
        self.calls=0
    def close(self):
        self.calls+=1
        if self.gate is not None:
            self.gate.wait(2)
        self.closed.set()

class ScopeCancellationTests(unittest.TestCase):
    def test_cancel_before_cleanup_finishes(self):
        gate=threading.Event();r=Resource(gate);s=NetworkResourceScope()
        self.assertTrue(s.register(r));self.assertFalse(s.cancelled)
        self.assertTrue(s.close());self.assertTrue(s.cancelled)
        self.assertFalse(s.wait_closed(.01))
        gate.set();self.assertTrue(s.wait_closed(2));self.assertEqual(r.calls,1)

    def test_close_is_idempotent_and_waitable(self):
        s=NetworkResourceScope();r=Resource();s.register(r)
        self.assertFalse(s.wait_closed(0));self.assertTrue(s.close())
        self.assertFalse(s.close());self.assertTrue(s.wait_closed(2))
        self.assertTrue(r.closed.is_set());self.assertEqual(r.calls,1)

    def test_late_registration_is_closed_once(self):
        s=NetworkResourceScope();s.close();self.assertTrue(s.wait_closed(2))
        r=Resource();self.assertFalse(s.register(r));self.assertEqual(r.calls,1)
