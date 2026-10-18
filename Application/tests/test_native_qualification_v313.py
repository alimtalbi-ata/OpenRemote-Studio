import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'02-Compilation'))
from analyze_qualification import analyze
class Native313(unittest.TestCase):
 def test_status_mismatch(self):
  with self.assertRaisesRegex(ValueError,'contradicts'):analyze({'steps':[{'name':'a','status':'PASS'}],'passed':1,'failed':0,'qualificationStatus':'FAIL'})
 def test_duplicate_skipped(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):analyze({'steps':[{'name':'a','status':'PASS'}],'passed':1,'failed':0,'skipped':['x','x']})
 def test_invalid_skipped(self):
  with self.assertRaisesRegex(ValueError,'invalid skipped'):analyze({'steps':[{'name':'a','status':'PASS'}],'passed':1,'failed':0,'skipped':'x'})
 def test_status_match(self):
  self.assertEqual(analyze({'steps':[{'name':'a','status':'FAIL','error':'bad'}],'passed':0,'failed':1,'qualificationStatus':'FAIL'})['status'],'FAIL')
 def test_native_script_and_no_stale_exit_checks(self):
  s=(ROOT/'02-Compilation/QUALIFICATION-NATIVE-V31.3.ps1').read_text()
  self.assertIn("if ($version -ne '31.3')",s)
  self.assertNotIn("if (-not $? -or $LASTEXITCODE -ne 0)",s)
