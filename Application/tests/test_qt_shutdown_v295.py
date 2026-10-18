import pathlib
import unittest


class ShutdownOrderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (pathlib.Path(__file__).resolve().parents[1] / 'qt_app.py').read_text(encoding='utf-8')
        cls.body = source.split('    def closeEvent(self,event):', 1)[1].split('    def lock_vault(', 1)[0]

    def test_sftp_guard_precedes_pty_stop(self):
        self.assertLess(self.body.index('if self.sftp_jobs:'), self.body.index('worker.stop()'))

    def test_sftp_refusal_returns_before_pty_stop(self):
        guard = self.body.split('for worker in self.findChildren(PtyShell):', 1)[0]
        self.assertIn('event.ignore();return', guard)

    def test_auxiliary_cleanup_follows_both_guards(self):
        self.assertLess(self.body.index('QTimer.singleShot(100,finish_window_shutdown)'), self.body.index('for proc in list(self.processes):'))
