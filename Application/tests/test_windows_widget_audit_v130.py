import unittest,json,subprocess
from unittest.mock import patch
import windows_widget_audit as a
class WidgetAuditTests(unittest.TestCase):
 def test_bad_timeouts(self):
  for t in (0,121,True,1.2):
   with self.assertRaises(ValueError):a.run_audit(timeout=t)
 def test_timeout(self):
  with patch.object(a.subprocess,'run',side_effect=subprocess.TimeoutExpired('x',1)):
   self.assertEqual(a.run_audit()['status'],'timeout')
 def test_launcher_error(self):
  with patch.object(a.subprocess,'run',side_effect=OSError('secret')):
   self.assertEqual(a.run_audit()['status'],'launcher_error')
 def test_success(self):
  payload={'checks':{k:True for k in ('search','tabs','tree','menu')},'clipped':[],'window':[900,600],'dpr':1.0}
  with patch.object(a.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'WIDGET_AUDIT_JSON='+json.dumps(payload),'')):
   self.assertEqual(a.run_audit()['status'],'passed')
 def test_failed_widget(self):
  payload={'checks':{k:True for k in ('search','tabs','tree','menu')}};payload['checks']['tree']=False
  with patch.object(a.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'WIDGET_AUDIT_JSON='+json.dumps(payload),'')):
   self.assertEqual(a.run_audit()['status'],'failed')
 def test_reject_invalid_payload(self):
  with patch.object(a.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'WIDGET_AUDIT_JSON={"checks":{"search":"yes"}}','')):
   self.assertEqual(a.run_audit()['status'],'failed')
 def test_no_network(self):
  self.assertNotIn('connect(',a.CHILD)
