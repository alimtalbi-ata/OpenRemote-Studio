import unittest
from ssh_troubleshooting_playbook import build_playbook,format_playbook

class PlaybookTests(unittest.TestCase):
 def test_success(self):
  p=build_playbook({'status':'authenticated','events':[]});self.assertFalse(p['hypotheses']);self.assertFalse(p['automatic_changes'])
 def test_failure_localized(self):
  p=build_playbook({'status':'failed','events':[{'step':'Bastion principal','state':'failed'}]});self.assertEqual(p['classification'],'failed_stage');self.assertIn('Bastion principal',p['evidence'][0])
 def test_failure_unlocated(self):
  self.assertEqual(build_playbook({'status':'failed','events':[]})['classification'],'unlocated_failure')
 def test_cancelled(self):
  self.assertEqual(build_playbook({'status':'cancelled','events':[]})['classification'],'cancelled')
 def test_invalid(self):
  with self.assertRaises(ValueError):build_playbook({'status':'unknown','events':[]})
 def test_no_sensitive_data(self):
  p=build_playbook({'status':'failed','events':[],'host':'private.example','password':'supersecret','message':'user admin@10.0.0.1'});s=str(p);self.assertNotIn('supersecret',s);self.assertNotIn('10.0.0.1',s);self.assertNotIn('private.example',s)
 def test_format(self):
  s=format_playbook(build_playbook({'status':'failed','events':[]}));self.assertIn('Constats observés',s);self.assertIn('Hypothèses non confirmées',s)
 def test_bad_format(self):
  with self.assertRaises(ValueError):format_playbook({})
 def test_no_mutation(self):
  p=build_playbook({'status':'failed','events':[]});self.assertFalse(p['automatic_changes']);self.assertTrue(all('instruction' in c for c in p['checks']))
