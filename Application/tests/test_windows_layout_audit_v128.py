import unittest
from unittest.mock import patch
import subprocess,json
import windows_layout_audit as a
class LayoutAuditTests(unittest.TestCase):
 def test_timeout_validation(self):
  for value in (0,121,1.5,True):
   with self.assertRaises(ValueError):a.run_audit(timeout=value)
 def test_timeout(self):
  with patch.object(a.subprocess,'run',side_effect=subprocess.TimeoutExpired('x',1)):
   self.assertEqual(a.run_audit()['status'],'timeout')
 def test_launcher_failure(self):
  with patch.object(a.subprocess,'run',side_effect=OSError('private path')):
   self.assertEqual(a.run_audit()['status'],'launcher_error')
 def test_success(self):
  data={'checks':{k:True for k in ('main_visible','main_positive_geometry','search_visible','search_nonzero_size','tabs_visible','tabs_nonzero_size','main_within_screen')},'screen':[1920,1080],'window':[800,600],'dpr':1.0}
  r=subprocess.CompletedProcess([],0,'LAYOUT_AUDIT_JSON='+json.dumps(data),'')
  with patch.object(a.subprocess,'run',return_value=r):
   result=a.run_audit();self.assertEqual(result['status'],'passed');self.assertEqual(result['geometry']['screen'],[1920,1080])
 def test_failed_check(self):
  data={'checks':{k:True for k in ('main_visible','main_positive_geometry','search_visible','search_nonzero_size','tabs_visible','tabs_nonzero_size','main_within_screen')}}
  data['checks']['main_within_screen']=False
  with patch.object(a.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'LAYOUT_AUDIT_JSON='+json.dumps(data),'')):
   self.assertEqual(a.run_audit()['status'],'failed')
 def test_bad_payload(self):
  with patch.object(a.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'LAYOUT_AUDIT_JSON={"checks":{"a":"yes"}}','')):
   self.assertEqual(a.run_audit()['status'],'failed')
 def test_child_no_network(self):
  self.assertNotIn('connect(',a.CHILD)
