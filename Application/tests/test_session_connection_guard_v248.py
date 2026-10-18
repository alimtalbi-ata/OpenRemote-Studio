import unittest
from session_connection_guard import ConnectionGuard, StaleAttempt
from session_lifecycle import State, InvalidTransition
class Resource:
    def __init__(self): self.closed=0
    def close(self): self.closed+=1
class GuardV248Tests(unittest.TestCase):
    def test_stale_resource_closed(self):
        g=ConnectionGuard('a'); old=g.begin();g.failure(old);new=g.begin();r=Resource()
        with self.assertRaises(StaleAttempt):g.success(old,r)
        self.assertEqual(r.closed,1);self.assertEqual(g.lifecycle.state,State.CONNECTING)
    def test_cancelled_resource_closed(self):
        g=ConnectionGuard('a');t=g.begin();g.cancel();r=Resource()
        with self.assertRaises(StaleAttempt):g.success(t,r)
        self.assertEqual(r.closed,1)
    def test_expired_resource_closed(self):
        g=ConnectionGuard('a',0);t=g.begin();r=Resource()
        with self.assertRaises(TimeoutError):g.success(t,r)
        self.assertEqual(r.closed,1);self.assertEqual(g.lifecycle.state,State.FAILED)
    def test_closed_resource_closed(self):
        g=ConnectionGuard('a');t=g.begin();g.close();r=Resource()
        with self.assertRaises(StaleAttempt):g.success(t,r)
        self.assertEqual(r.closed,1)
if __name__=='__main__':unittest.main()
