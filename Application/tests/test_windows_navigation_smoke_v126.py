import unittest
from unittest.mock import patch
import subprocess
import json
from windows_navigation_smoke import run_smoke, SCHEMA

class TestNavigationSmoke(unittest.TestCase):
    def test_invalid_timeout(self):
        for v in (0, 121, True, 2.5, '5'):
            with self.assertRaises(ValueError):run_smoke(timeout=v)
    @patch('windows_navigation_smoke.subprocess.run')
    def test_pass(self, run):
        run.return_value=subprocess.CompletedProcess([],0,'NAV_SMOKE_JSON='+json.dumps({'menus':True,'focus':True})+'\n','')
        result=run_smoke(timeout=8)
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['schema'],SCHEMA)
        self.assertFalse(result['network_tests_executed'])
        self.assertEqual(run.call_args.kwargs['env']['QT_QPA_PLATFORM'],'offscreen')
    @patch('windows_navigation_smoke.subprocess.run')
    def test_failed_check(self, run):
        run.return_value=subprocess.CompletedProcess([],0,'NAV_SMOKE_JSON={"menus":false}\n','')
        self.assertEqual(run_smoke()['status'],'failed')
    @patch('windows_navigation_smoke.subprocess.run')
    def test_malformed_output(self, run):
        run.return_value=subprocess.CompletedProcess([],0,'NAV_SMOKE_JSON={broken','secret')
        self.assertEqual(run_smoke()['checks'],{})
        self.assertNotIn('secret',str(run_smoke()))
    @patch('windows_navigation_smoke.subprocess.run',side_effect=subprocess.TimeoutExpired('python',2))
    def test_timeout(self,run):self.assertEqual(run_smoke()['status'],'timeout')
    @patch('windows_navigation_smoke.subprocess.run',side_effect=OSError('secret'))
    def test_launcher_error(self,run):self.assertEqual(run_smoke()['status'],'launcher_error')
