import pathlib,unittest

class ShutdownContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src=(pathlib.Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        cls.body=src.split('    def closeEvent(self,event):',1)[1].split('    def lock_vault(',1)[0]
    def test_processes_stopped_after_pty_guard(self):
        self.assertLess(self.body.index('event.ignore();return'),self.body.index('for proc in list(self.processes):'))
    def test_processes_stopped_after_sftp_guard(self):
        self.assertLess(self.body.index("if self.sftp_jobs:"),self.body.index('for proc in list(self.processes):'))
    def test_shutdown_reaps_auxiliary_processes(self):
        self.assertIn('proc.kill()',self.body)
        self.assertIn('proc.waitForFinished(1000)',self.body)
        self.assertIn('self.processes.remove(proc)',self.body)
