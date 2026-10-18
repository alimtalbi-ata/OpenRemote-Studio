import json,subprocess,unittest
from unittest.mock import patch
import windows_dialog_audit as a
class DialogAuditTests(unittest.TestCase):
 def payload(self,valid=True):
  return {'checks':{name:{k:(valid or name!='connection') for k in ('visible','within_screen','has_action_buttons','positive_size')} for name in a.EXPECTED}}
 def mocked(self,payload,code=0):
  return subprocess.CompletedProcess([],code,'DIALOG_AUDIT_JSON='+json.dumps(payload),'')
 def test_success(self):
  with patch.object(a.subprocess,'run',return_value=self.mocked(self.payload())):self.assertEqual(a.run_audit()['status'],'passed')
 def test_failed_check(self):
  with patch.object(a.subprocess,'run',return_value=self.mocked(self.payload(False))):self.assertEqual(a.run_audit()['status'],'failed')
 def test_bad_payload(self):self.assertIsNone(a.validate_payload({'checks':{'connection':{}}}))
 def test_bad_boolean(self):
  payload=self.payload();payload['checks']['connection']['visible']='true';self.assertIsNone(a.validate_payload(payload))
 def test_timeout(self):
  with patch.object(a.subprocess,'run',side_effect=subprocess.TimeoutExpired('x',1)):self.assertEqual(a.run_audit()['status'],'timeout')
 def test_launch_error(self):
  with patch.object(a.subprocess,'run',side_effect=OSError('private')):self.assertEqual(a.run_audit()['status'],'launcher_error')
 def test_invalid_timeout(self):
  for value in (0,121,True,1.5):
   with self.assertRaises(ValueError):a.run_audit(timeout=value)
 def test_no_network(self):self.assertNotIn('connect(',a.CHILD)
