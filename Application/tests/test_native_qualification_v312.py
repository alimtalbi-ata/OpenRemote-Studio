import unittest,sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'02-Compilation'))
from analyze_qualification import analyze
class Native312(unittest.TestCase):
 def test_script_quotes_closed(self):
  script=(ROOT/'02-Compilation/QUALIFICATION-NATIVE-V31.2.ps1').read_text()
  self.assertIn('Write-Host "Qualification JSON: $jsonPath"',script)
  self.assertIn('Write-Host "Qualification report: $report"',script)
  self.assertIn("status='FAIL'; seconds=0",script)
 def test_success(self):
  self.assertEqual(analyze({'steps':[{'name':'Build','status':'PASS'}],'passed':1,'failed':0})['status'],'PASS')
 def test_failure(self):
  self.assertEqual(analyze({'steps':[{'name':'Build','status':'FAIL','error':'code 1'}],'passed':0,'failed':1})['failures'][0]['error'],'code 1')
 def test_missing_evidence_rejected(self):
  with self.assertRaises(ValueError):analyze({'steps':[],'passed':0,'failed':0})
 def test_mismatch_rejected(self):
  with self.assertRaises(ValueError):analyze({'steps':[{'name':'Build','status':'PASS'}],'passed':1,'failed':1})
