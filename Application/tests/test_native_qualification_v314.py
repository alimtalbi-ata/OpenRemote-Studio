import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'02-Compilation'))
from analyze_qualification import analyze
class Native314(unittest.TestCase):
 def test_partial_when_skipped(self):
  self.assertEqual(analyze({'steps':[{'name':'Published release exists','status':'PASS'}],'passed':1,'failed':0,'skipped':['Build'],'qualificationStatus':'PARTIAL'})['status'],'PARTIAL')
 def test_false_pass_rejected(self):
  with self.assertRaisesRegex(ValueError,'contradicts'):analyze({'steps':[{'name':'a','status':'PASS'}],'passed':1,'failed':0,'skipped':['Installer validation'],'qualificationStatus':'PASS'})
 def test_failed_dominates_skipped(self):
  self.assertEqual(analyze({'steps':[{'name':'a','status':'FAIL'}],'passed':0,'failed':1,'skipped':['Build'],'qualificationStatus':'FAIL'})['status'],'FAIL')
 def test_native_script_marks_partial(self):
  s=(ROOT/'02-Compilation/QUALIFICATION-NATIVE-V31.4.ps1').read_text()
  self.assertIn("{ 'PARTIAL' }",s)
  self.assertIn("if ($version -ne '31.4')",s)
