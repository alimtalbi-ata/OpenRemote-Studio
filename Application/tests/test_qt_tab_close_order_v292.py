import pathlib, unittest
class TabCloseOrderingContract(unittest.TestCase):
    def test_pty_must_stop_before_processes_are_killed(self):
        source=(pathlib.Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        body=source.split('    def close_tab(self,index):',1)[1].split('    def show_integrations(',1)[0]
        self.assertLess(body.index('worker.stop()'),body.index('for proc in list(self.processes):'))
        self.assertLess(body.index('QTimer.singleShot(100,finish_when_stopped)'),body.index('proc.kill()'))
        self.assertIn('return',body.split('QTimer.singleShot(100,finish_when_stopped)',1)[1].split('for proc in list(self.processes):',1)[0])
