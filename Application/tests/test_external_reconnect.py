import unittest
from external_sessions import ExternalSessionRegistry
class FakeProcess:
 def __init__(self,pid,code=None):self.pid=pid;self.code=code
 def poll(self):return self.code
class ReconnectTests(unittest.TestCase):
 def test_running_blocks_duplicate(self):
  r=ExternalSessionRegistry();r.register({'id':'a','name':'one','protocol':'SSH'},FakeProcess(42))
  self.assertTrue(r.has_running('a'))
  self.assertIsNone(r.reconnect_candidate('a'))
 def test_exited_can_reconnect(self):
  r=ExternalSessionRegistry();r.register({'id':'a','name':'one','protocol':'SSH'},FakeProcess(42,0))
  self.assertFalse(r.has_running('a'))
  self.assertEqual(r.reconnect_candidate('a',42)['pid'],42)
 def test_no_cross_connection(self):
  r=ExternalSessionRegistry();r.register({'id':'a','name':'one','protocol':'SSH'},FakeProcess(42,1))
  self.assertIsNone(r.reconnect_candidate('b'))
 def test_latest_exited(self):
  r=ExternalSessionRegistry()
  for pid in (42,43):r.register({'id':'a','name':'one','protocol':'SSH'},FakeProcess(pid,0))
  self.assertEqual(r.reconnect_candidate('a',43)['pid'],43)
