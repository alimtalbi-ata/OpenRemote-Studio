import unittest
from guarded_ssh_adapter import GuardedSSHAdapter
from session_lifecycle import State
from session_connection_guard import StaleAttempt

class Resource:
    def __init__(self): self.closed=False
    def close(self): self.closed=True

class TestGuardedSSHAdapter(unittest.TestCase):
    def test_success_and_close(self):
        resource=Resource(); adapter=GuardedSSHAdapter('ssh-1',lambda:resource)
        self.assertIs(adapter.connect(),resource)
        adapter.close(); self.assertTrue(resource.closed)
        self.assertEqual(adapter.guard.lifecycle.state,State.CLOSED)
    def test_late_success_after_cancel_is_closed(self):
        resource=Resource(); adapter=None
        def factory():
            adapter.cancel(); return resource
        adapter=GuardedSSHAdapter('ssh-2',factory)
        with self.assertRaises(StaleAttempt):adapter.connect()
        self.assertTrue(resource.closed)
    def test_failed_factory_preserves_error(self):
        def factory():raise OSError('offline')
        adapter=GuardedSSHAdapter('ssh-3',factory)
        with self.assertRaises(OSError):adapter.connect()
        self.assertEqual(adapter.guard.lifecycle.state,State.FAILED)
