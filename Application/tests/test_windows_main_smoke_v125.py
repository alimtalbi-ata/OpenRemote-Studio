import unittest
from unittest.mock import patch
import subprocess
from windows_main_smoke import run_smoke

class TestMainSmoke(unittest.TestCase):
    def test_timeout_validation(self):
        for v in (0,121,True,1.5):
            with self.assertRaises(ValueError):run_smoke(timeout=v)
    @patch('windows_main_smoke.subprocess.run')
    def test_success(self,run):
        run.return_value=subprocess.CompletedProcess([],0,'MAIN_SMOKE_OK\n','')
        result=run_smoke(timeout=7)
        self.assertEqual(result['status'],'passed')
        self.assertTrue(result['main_window_tested'])
        self.assertFalse(result['network_tests_executed'])
        self.assertEqual(run.call_args.kwargs['env']['QT_QPA_PLATFORM'],'offscreen')
    @patch('windows_main_smoke.subprocess.run')
    def test_failed_redacted(self,run):
        run.return_value=subprocess.CompletedProcess([],1,'','secret password')
        self.assertNotIn('secret',str(run_smoke()))
    @patch('windows_main_smoke.subprocess.run',side_effect=subprocess.TimeoutExpired('python',3))
    def test_timeout(self,run):self.assertEqual(run_smoke()['status'],'timeout')
    @patch('windows_main_smoke.subprocess.run',side_effect=OSError('private'))
    def test_error(self,run):self.assertEqual(run_smoke()['status'],'launcher_error')
