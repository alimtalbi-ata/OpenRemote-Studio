import copy,json,tempfile,unittest
from pathlib import Path
from pam_lab_reports import make_report,verify_report,export_report
from pam_lab_scenarios import run_scenarios
class PamLabReportsTests(unittest.TestCase):
 def test_empty_report(self):self.assertTrue(verify_report(make_report([])))
 def test_hash_chain(self):
  report=make_report([{'decision':'DENY'},{'decision':'SIMULATED_ONLY'}])
  self.assertTrue(verify_report(report))
  changed=copy.deepcopy(report);changed['events'][0]['event']['decision']='ALLOW'
  self.assertFalse(verify_report(changed))
 def test_reorder_detected(self):
  report=make_report([{'n':1},{'n':2}]);report['events'].reverse()
  self.assertFalse(verify_report(report))
 def test_export(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'audit.json'
   report=export_report(path,[{'action':'authorize','decision':'DENY'}])
   self.assertEqual(json.loads(path.read_text())['final_hash'],report['final_hash'])
   self.assertTrue(verify_report(json.loads(path.read_text())))
 def test_scenarios(self):
  result=run_scenarios()
  self.assertTrue(result['passed'])
  self.assertEqual(len(result['results']),6)
  self.assertGreater(len(result['audit']),0)
