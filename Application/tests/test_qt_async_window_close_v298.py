from pathlib import Path
import unittest

class AsyncWindowCloseContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        cls.body=source.split('    def closeEvent(self,event):',1)[1].split('    def lock_vault(',1)[0]
    def test_no_blocking_pty_wait(self):
        self.assertNotIn('worker.wait(',self.body)
        self.assertIn('QTimer.singleShot(100,finish_window_shutdown)',self.body)
    def test_refused_close_preserves_helpers(self):
        self.assertLess(self.body.index('if self.sftp_jobs:'),self.body.index('for proc in list(self.processes):'))
        self.assertLess(self.body.index('event.ignore()'),self.body.index('for proc in list(self.processes):'))
    def test_timeout_and_retry(self):
        self.assertIn('self._window_close_attempts>=30',self.body)
        self.assertIn('self._window_close_pending=False',self.body)
        self.assertIn('self.close()',self.body)
