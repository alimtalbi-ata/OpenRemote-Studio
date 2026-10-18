import unittest
from ssh_failure_guidance import classify
class GuidanceTests(unittest.TestCase):
    def test_success(self):self.assertEqual(classify({'status':'authenticated','events':[]})['code'],'authenticated')
    def test_cancel(self):self.assertEqual(classify({'status':'cancelled','events':[]})['code'],'cancelled')
    def test_failure_unknown(self):self.assertEqual(classify({'status':'failed','events':[]})['code'],'unlocated_failure')
    def test_failure_stage(self):
        r=classify({'status':'failed','events':[{'step':'Bastion principal','state':'failed'}]})
        self.assertEqual(r['stage'],'Bastion principal')
    def test_slow(self):self.assertEqual(classify({'status':'authenticated','events':[{'step':'Serveur cible','state':'ok','duration_ms':2200}]})['code'],'slow_stage')
    def test_fast(self):self.assertEqual(classify({'status':'authenticated','events':[{'step':'Serveur cible','state':'ok','duration_ms':200}]})['code'],'authenticated')
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):classify({'status':'failed','events':[]},0)
    def test_invalid_status(self):
        with self.assertRaises(ValueError):classify({'status':'unknown','events':[]})
    def test_no_host_in_guidance(self):
        r=classify({'status':'failed','events':[{'step':'Serveur cible','state':'failed'}],'message':'secret.example user=admin'})
        self.assertNotIn('secret.example',str(r));self.assertNotIn('admin',str(r))
