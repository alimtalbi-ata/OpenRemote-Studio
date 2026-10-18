import unittest,subprocess,json
from unittest.mock import patch
from windows_accessibility_smoke import run_smoke,SCHEMA
class TestAccessibilitySmoke(unittest.TestCase):
 def test_invalid_timeout(self):
  for v in (0,121,True,2.5,'5'):
   with self.assertRaises(ValueError):run_smoke(timeout=v)
 @patch('windows_accessibility_smoke.subprocess.run')
 def test_pass(self,run):
  run.return_value=subprocess.CompletedProcess([],0,'ACCESS_SMOKE_JSON='+json.dumps({'focus':True,'shortcut':True})+'\n','')
  result=run_smoke();self.assertEqual(result['status'],'passed');self.assertEqual(result['schema'],SCHEMA)
  self.assertFalse(result['network_tests_executed'])
 @patch('windows_accessibility_smoke.subprocess.run')
 def test_fail(self,run):
  run.return_value=subprocess.CompletedProcess([],0,'ACCESS_SMOKE_JSON={"focus":false}\n','')
  self.assertEqual(run_smoke()['status'],'failed')
 @patch('windows_accessibility_smoke.subprocess.run')
 def test_bad_output(self,run):
  run.return_value=subprocess.CompletedProcess([],0,'ACCESS_SMOKE_JSON=bad','secret')
  self.assertEqual(run_smoke()['checks'],{})
  self.assertNotIn('secret',str(run_smoke()))
 @patch('windows_accessibility_smoke.subprocess.run',side_effect=subprocess.TimeoutExpired('python',1))
 def test_timeout(self,run):self.assertEqual(run_smoke()['status'],'timeout')
 @patch('windows_accessibility_smoke.subprocess.run',side_effect=OSError('secret'))
 def test_launch_error(self,run):self.assertEqual(run_smoke()['status'],'launcher_error')
