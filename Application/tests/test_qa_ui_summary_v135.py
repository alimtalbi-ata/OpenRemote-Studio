import unittest,tempfile,json
from pathlib import Path
from qa_ui_summary import format_campaign,load_summary
from qa_anomaly_summary import CHECKS

class SummaryTests(unittest.TestCase):
 def report(self,status='passed'):
  return {'schema':'openremote.windows-qa-campaign.v1','reports':{x:{'status':status,'secret':'PASSWORD=topsecret','host':'private.example'} for x in CHECKS}}
 def test_success(self):
  result=format_campaign(self.report());self.assertIn('Réussi',result);self.assertIn('NON VALIDÉES',result)
 def test_secrets_filtered(self):
  result=format_campaign(self.report());self.assertNotIn('topsecret',result);self.assertNotIn('private.example',result)
 def test_incomplete(self):self.assertIn('incomplète',format_campaign(self.report('blocked')))
 def test_failed(self):self.assertIn('Anomalies',format_campaign(self.report('failed')))
 def test_reject_invalid_schema(self):
  with self.assertRaises(ValueError):format_campaign({'schema':'other','reports':{}})
 def test_missing_file(self):
  with tempfile.TemporaryDirectory() as d:self.assertIn('Aucun rapport',load_summary(Path(d)/'none.json'))
 def test_load_valid(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'qa.json';p.write_text(json.dumps(self.report()),encoding='utf8');self.assertIn('Navigation',load_summary(p))
 def test_reject_large(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'qa.json';p.write_bytes(b'x'*1048577)
   with self.assertRaises(ValueError):load_summary(p)
if __name__=='__main__':unittest.main()
