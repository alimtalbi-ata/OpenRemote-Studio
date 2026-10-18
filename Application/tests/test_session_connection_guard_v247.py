import unittest
from session_connection_guard import ConnectionGuard,StaleAttempt
from session_lifecycle import State,InvalidTransition
class Dummy:
 def __init__(self):self.closed=False
 def close(self):self.closed=True
class GuardTests(unittest.TestCase):
 def test_success_close(self):
  g=ConnectionGuard('a');t=g.begin();d=Dummy();g.success(t,d);g.close();self.assertTrue(d.closed);self.assertEqual(g.lifecycle.state,State.CLOSED)
 def test_stale_after_retry(self):
  g=ConnectionGuard('a');t=g.begin();g.failure(t);u=g.begin();self.assertRaises(StaleAttempt,g.success,t,Dummy());g.success(u,Dummy())
 def test_cancel_invalidates(self):
  g=ConnectionGuard('a');t=g.begin();g.cancel();self.assertRaises(StaleAttempt,g.success,t,Dummy())
 def test_timeout(self):
  g=ConnectionGuard('a',1);t=g.begin();self.assertTrue(g.expire(g.lifecycle.started_at+2));self.assertRaises(InvalidTransition,g.success,t,Dummy())
 def test_close_idempotent(self):
  g=ConnectionGuard('a');g.close();g.close();self.assertEqual(g.lifecycle.state,State.CLOSED)
 def test_close_failure(self):
  class Bad:
   def close(self):raise OSError('close failed')
  g=ConnectionGuard('a');t=g.begin();g.success(t,Bad());self.assertRaises(OSError,g.close);self.assertEqual(g.lifecycle.state,State.FAILED)
if __name__=='__main__':unittest.main()
