import unittest
from session_diagnostics import explain_session_failure, format_guided_diagnostic
class TestGuidanceV227(unittest.TestCase):
 def test_failure(self):
  x=explain_session_failure({'status':'exited','exit_code':255,'protocol':'SSH'});self.assertEqual(x['code'],'LOCAL_PROCESS_EXIT_NONZERO');self.assertFalse(x['safe_to_retry']);self.assertTrue(x['actions'])
 def test_unknown_blocks(self):
  self.assertFalse(explain_session_failure({'status':'unknown','protocol':'RDP'})['safe_to_retry'])
 def test_running(self):
  self.assertEqual(explain_session_failure({'status':'running'})['severity'],'info')
 def test_missing_exit(self):
  self.assertEqual(explain_session_failure({'status':'exited','exit_code':None})['code'],'SESSION_INCOMPLETE')
 def test_bool_not_exit_code(self):
  self.assertEqual(explain_session_failure({'status':'exited','exit_code':True})['code'],'SESSION_INCOMPLETE')
 def test_format(self):
  self.assertIn('Verifications',format_guided_diagnostic({'status':'exited','exit_code':1,'protocol':'SFTP'}))
if __name__=='__main__':unittest.main()
