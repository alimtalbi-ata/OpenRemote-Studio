import pathlib
import unittest

SOURCE = (pathlib.Path(__file__).resolve().parents[1] / 'qt_app.py').read_text(encoding='utf-8')

class AsyncTabCloseContract(unittest.TestCase):
    def test_polling_uses_qt_timer(self):
        method = SOURCE.split('    def close_tab(self,index):',1)[1].split('    def show_integrations(self):',1)[0]
        self.assertIn('QTimer.singleShot(100,finish_when_stopped)', method)
        self.assertIn('self.tabs.indexOf(widget)', method)
        self.assertNotIn('worker.wait(', method)
    def test_refused_close_preserves_widget(self):
        method = SOURCE.split('    def close_tab(self,index):',1)[1].split('    def show_integrations(self):',1)[0]
        self.assertIn('widget._ssh_close_pending=False', method)
        self.assertIn('widget._ssh_close_attempts >= 30', method)
        self.assertLess(method.index('if active:'), method.index('cancel_sftp=getattr'))
