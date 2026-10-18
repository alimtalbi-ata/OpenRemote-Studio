import tempfile,unittest
from pathlib import Path
from pam_lab_reports import make_report,verify_report,load_and_verify_report,export_report
class VerifyAuditTests(unittest.TestCase):
 def test_round_trip(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'audit.json';export_report(p,[{'action':'deny','decision':'DENY'}])
   self.assertTrue(load_and_verify_report(p)['valid'])
 def test_tamper_detected(self):
  report=make_report([{'action':'deny'}]);report['events'][0]['event']['action']='allow'
  self.assertFalse(verify_report(report))
 def test_unknown_metadata_rejected(self):
  report=make_report([]);report['unexpected']='value'
  self.assertFalse(verify_report(report))
 def test_event_extra_fields_rejected(self):
  report=make_report([{'action':'deny'}]);report['events'][0]['untrusted']='value'
  self.assertFalse(verify_report(report))
 def test_oversized_file(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'big.json';p.write_bytes(b' '*200)
   with self.assertRaises(ValueError):load_and_verify_report(p,max_bytes=100)
 def test_invalid_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.json';p.write_text('{not json')
   with self.assertRaises(ValueError):load_and_verify_report(p)
 def test_ui_action(self):
  text=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  self.assertIn('Vérifier audit JSON',text)
  self.assertIn('verify_audit.clicked.connect(verify_events)',text)
