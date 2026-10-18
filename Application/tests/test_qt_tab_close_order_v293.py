import pathlib, unittest

class TabCloseSftpOrderingContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src=(pathlib.Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        cls.body=src.split('    def close_tab(self,index):',1)[1].split('    def show_integrations(',1)[0]
    def test_cancel_before_auxiliary_process_termination(self):
        self.assertLess(self.body.index('cancel_sftp()'),self.body.index('proc.kill()'))
    def test_pty_failure_keeps_sftp_callbacks_alive(self):
        self.assertLess(self.body.index('if active:'),self.body.index('widget._sftp_closing=True'))
        self.assertIn('return',self.body.split('if active:',1)[1].split('widget._sftp_closing=True',1)[0])
