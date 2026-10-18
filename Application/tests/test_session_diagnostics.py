import unittest
from session_diagnostics import analyze_sessions,summarize_diagnostics
class SessionDiagnosticsTests(unittest.TestCase):
 def row(self,code,protocol='SSH',id='server'):
  return {'connection_id':id,'name':id,'protocol':protocol,'status':'exited' if code is not None else 'running','exit_code':code}
 def test_repeated_failures(self):
  result=analyze_sessions([self.row(255),self.row(255)])
  self.assertTrue(result[0]['repeated_failure'])
  self.assertEqual(result[0]['failures'],2)
 def test_one_failure_not_repeated(self):
  self.assertFalse(analyze_sessions([self.row(255)])[0]['repeated_failure'])
 def test_success_and_active_not_failures(self):
  result=analyze_sessions([self.row(0),self.row(None)])[0]
  self.assertEqual(result['failures'],0)
  self.assertEqual(result['active_processes'],1)
 def test_groups_isolated(self):
  result=summarize_diagnostics([self.row(1,id='a'),self.row(2,id='a'),self.row(3,id='b')])
  self.assertEqual(result['repeated_failures'],1)
  self.assertEqual(result['failed_attempts'],3)
 def test_boolean_code_not_failure(self):
  self.assertEqual(analyze_sessions([self.row(True)])[0]['failures'],0)
 def test_invalid_threshold(self):
  with self.assertRaises(ValueError):analyze_sessions([],1)
 def test_hints_no_remote_actions(self):
  self.assertIn('RD Gateway',analyze_sessions([self.row(1,protocol='RDP')])[0]['hint'])
