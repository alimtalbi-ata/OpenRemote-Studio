import unittest
from unittest.mock import patch
import subprocess
from windows_gui_smoke import run_smoke

class TestQtSmoke(unittest.TestCase):
    def test_invalid_timeout(self):
        for value in (0, 121, True, 1.2):
            with self.assertRaises(ValueError): run_smoke(timeout=value)
    @patch('windows_gui_smoke.subprocess.run')
    def test_success(self, run):
        run.return_value=subprocess.CompletedProcess([],0,'QT_SMOKE_OK\n','')
        r=run_smoke(timeout=5)
        self.assertEqual(r['status'],'passed')
        self.assertFalse(r['main_window_tested'])
        self.assertFalse(r['network_tests_executed'])
        self.assertEqual(run.call_args.kwargs['timeout'],5)
    @patch('windows_gui_smoke.subprocess.run')
    def test_failed(self, run):
        run.return_value=subprocess.CompletedProcess([],1,'','sensitive error')
        r=run_smoke()
        self.assertEqual(r['status'],'failed')
        self.assertNotIn('sensitive',str(r))
    @patch('windows_gui_smoke.subprocess.run',side_effect=subprocess.TimeoutExpired(['python'],3))
    def test_timeout(self, run): self.assertEqual(run_smoke()['status'],'timeout')
    @patch('windows_gui_smoke.subprocess.run',side_effect=OSError('private path'))
    def test_launcher_error(self, run): self.assertEqual(run_smoke()['status'],'launcher_error')
