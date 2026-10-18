import unittest
from external_sessions import ExternalSessionRegistry
class FakeProcess:
 def __init__(self,pid=123,code=None):self.pid=pid;self.code=code
 def poll(self):return self.code
class ExternalSessionTests(unittest.TestCase):
 def setUp(self):
  self.registry=ExternalSessionRegistry()
  self.conn={'id':'abc','name':'prod-server','protocol':'SSH'}
 def test_running(self):
  self.registry.register(self.conn,FakeProcess())
  self.assertEqual(self.registry.snapshot()[0]['status'],'running')
 def test_exited(self):
  proc=FakeProcess();self.registry.register(self.conn,proc);proc.code=12
  self.assertEqual(self.registry.snapshot()[0]['exit_code'],12)
 def test_cleanup_only_exited(self):
  a=FakeProcess(1,0);b=FakeProcess(2,None)
  self.registry.register(self.conn,a);self.registry.register(self.conn,b)
  self.assertEqual(self.registry.clear_exited(),1)
  self.assertEqual(self.registry.snapshot()[0]['pid'],2)
 def test_invalid_pid(self):
  with self.assertRaises(ValueError):self.registry.register(self.conn,FakeProcess(0))
 def test_no_kill(self):
  proc=FakeProcess();self.registry.register(self.conn,proc)
  self.registry.clear_exited()
  self.assertEqual(len(self.registry.snapshot()),1)
