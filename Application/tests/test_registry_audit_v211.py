import unittest
from external_sessions import ExternalSessionRegistry
from session_reconnect_choices import reconnectable_processes

class Proc:
 def __init__(self,pid=11,code=None,fail=False):self.pid=pid;self.code=code;self.fail=fail
 def poll(self):
  if self.fail:raise OSError('process handle invalid')
  return self.code
class History:
 def __init__(self):self.starts=[];self.finishes=[];self.fail=False
 def started(self,row):self.starts.append(row)
 def finished(self,row):
  if self.fail:raise OSError('disk unavailable')
  self.finishes.append(row)
class AuditTests(unittest.TestCase):
 def conn(self,id='a'):return {'id':id,'name':'test','protocol':'SSH'}
 def test_finish_written_once_across_refreshes(self):
  h=History();r=ExternalSessionRegistry(h);p=Proc(code=0);r.register(self.conn(),p)
  for _ in range(8):r.snapshot()
  self.assertEqual(len(h.finishes),1)
 def test_history_failure_retries(self):
  h=History();h.fail=True;r=ExternalSessionRegistry(h);r.register(self.conn(),Proc(code=4))
  r.snapshot();self.assertEqual(len(h.finishes),0)
  h.fail=False;r.snapshot();r.snapshot();self.assertEqual(len(h.finishes),1)
 def test_unknown_not_misreported_running(self):
  r=ExternalSessionRegistry();r.register(self.conn(),Proc(fail=True))
  self.assertEqual(r.snapshot()[0]['status'],'unknown')
 def test_unknown_blocks_new_launch(self):
  r=ExternalSessionRegistry();r.register(self.conn(),Proc(fail=True))
  self.assertTrue(r.has_running('a'))
 def test_unknown_sibling_blocks_reconnect(self):
  r=ExternalSessionRegistry();r.register(self.conn(),Proc(11,1));r.register(self.conn(),Proc(12,fail=True))
  self.assertEqual(reconnectable_processes(r.snapshot(),'a'),[])
  self.assertIsNone(r.reconnect_candidate('a',11))
 def test_unknown_preserved_during_cleanup(self):
  r=ExternalSessionRegistry();r.register(self.conn(),Proc(fail=True))
  self.assertEqual(r.clear_exited(),0)
 def test_other_connection_not_blocked(self):
  r=ExternalSessionRegistry();r.register(self.conn(),Proc(11,fail=True));r.register(self.conn('b'),Proc(12,1))
  self.assertEqual(len(reconnectable_processes(r.snapshot(),'b')),1)
