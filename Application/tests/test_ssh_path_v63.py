import unittest,subprocess
from ssh_path_probe import command,check
C={'protocol':'SSH','host':'server.internal','port':'22'}
R={'mode':'ssh_jump','jump_host':'bastion.internal','jump_port':'2222','jump_user':'ops'}
class Tests(unittest.TestCase):
 def test_safe_command(self):
  args=command(C,R)
  self.assertIn('BatchMode=yes',args)
  self.assertIn('StrictHostKeyChecking=yes',args)
  self.assertEqual(args[-1],'ops@bastion.internal')
  self.assertIn('server.internal:22',args)
 def test_reject_direct(self):
  with self.assertRaises(ValueError):command(C,{'mode':'direct'})
 def test_reject_target_injection(self):
  with self.assertRaises(ValueError):command(dict(C,host='-oProxyCommand=evil'),R)
 def test_reject_other_protocol(self):
  with self.assertRaises(ValueError):command(dict(C,protocol='RDP'),R)
 def test_result(self):
  calls=[]
  def runner(args,**kw):
   calls.append((args,kw));return subprocess.CompletedProcess(args,0)
  self.assertTrue(check(C,R,runner=runner)['reachable'])
  self.assertEqual(calls[0][1]['stdin'],subprocess.DEVNULL)
 def test_timeout(self):
  with self.assertRaises(ValueError):command(C,R,timeout=20)
