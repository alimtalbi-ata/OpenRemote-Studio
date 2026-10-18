import unittest,subprocess
from ssh_path_probe import classify,check
C={'protocol':'SSH','host':'server.internal','port':'22'}
R={'mode':'ssh_jump','jump_host':'bastion.internal','jump_port':'2222','jump_user':'ops'}
class TestV64(unittest.TestCase):
 def test_timeout_indeterminate(self):
  def run(*a,**k):raise subprocess.TimeoutExpired('ssh',7)
  self.assertEqual(check(C,R,runner=run)['status'],'indeterminate')
 def test_bastion_auth(self):
  self.assertEqual(classify(255,b'Permission denied (publickey)')['status'],'bastion_auth_or_trust')
 def test_target_refused(self):
  self.assertEqual(classify(255,b'channel 0: open failed: connect failed: Connection refused')['status'],'target_channel_failed')
 def test_sanitize_output(self):
  self.assertNotIn('secret-user',classify(255,b'error secret-user')['message'])
 def test_success_not_application_auth(self):
  r=classify(0);self.assertTrue(r['reachable']);self.assertIn('non vérifiée',r['message'])
 def test_unknown(self):
  self.assertEqual(classify(255,b'unexpected')['status'],'unclassified_failure')
