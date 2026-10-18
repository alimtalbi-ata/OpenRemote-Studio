import json,unittest
from connection_diagnostics import json_report
from launch_plan import build_launch_plan
class DiagnosticTests(unittest.TestCase):
 def conn(self,p='SSH',host='server.example'):
  return {'name':'Production','protocol':p,'host':host,'port':'','user':'admin'}
 def test_report_ready(self):
  data=json.loads(json_report(self.conn(),which=lambda x:'/usr/bin/'+x,platform='posix'))
  self.assertTrue(data['local_ready']);self.assertEqual(data['schema'],'openremote.access.v1')
 def test_pam_fails_closed(self):
  data=json.loads(json_report(self.conn(),{'mode':'direct','vault_ref':'cyberark:Safe/A'},which=lambda x:'/usr/bin/'+x,platform='posix'))
  self.assertFalse(data['local_ready']);self.assertTrue(data['pam_required'])
  self.assertNotIn('Safe/A',json.dumps(data))
 def test_web_report_redacts_query(self):
  data=json.loads(json_report(self.conn('WEB','https://example.com/path?token=very-secret'),which=lambda x:None,platform='nt'))
  self.assertEqual(data['target'],'example.com');self.assertNotIn('very-secret',json.dumps(data))
 def test_web_rejects_unsafe_schemes(self):
  for url in ('javascript:alert(1)','ftp://example.com','https://user:pass@example.com','https://example.com/#secret'):
   with self.subTest(url=url),self.assertRaises(ValueError):
    build_launch_plan(self.conn('WEB',url),which=lambda x:None,platform='nt')
 def test_missing_client(self):
  data=json.loads(json_report(self.conn(),which=lambda x:None,platform='posix'))
  self.assertFalse(data['local_ready'])
