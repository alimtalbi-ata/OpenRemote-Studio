"""R82 Qt operator flow using fake controller: no SSH connection is made."""
import unittest
try:
    from PySide6.QtWidgets import QApplication
    from ssh_tunnel_qt import SSHTunnelPanel
except ImportError:
    QApplication=None


class FakeController:
    def __init__(self):
        self.started=0
        self.stopped=0
        self.done=False
    def start(self,*a,**k):self.started+=1
    def stop(self):self.stopped+=1
    def poll(self):
        from tunnel_controller import TunnelSnapshot
        return TunnelSnapshot('closed' if self.done else 'active')
    def is_shutdown_complete(self):return self.done


@unittest.skipIf(QApplication is None,'PySide6 unavailable; run in Windows CI')
class QtTunnelR82(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_offline_by_default_and_revoke_is_async(self):
        panel=SSHTunnelPanel({'protocol':'SSH','host':'example.test'},controller_factory=FakeController)
        self.assertFalse(panel.consent.isChecked())
        self.assertEqual(panel._controller.started,0)
        panel.start_tunnel()
        self.assertEqual(panel._controller.started,0)
        self.assertIn('autorisation',panel.status.text())
        called=[]
        self.assertFalse(panel.request_close(lambda:called.append(1)))
        self.assertEqual(panel._controller.stopped,1)
        panel._controller.done=True
        panel._refresh();self.app.processEvents()
        self.assertEqual(called,[1])
        panel.close()

    def test_menu_integration_and_window_shutdown_contract(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('Tunnel SSH local (sécurisé)',source)
        self.assertIn('panel.request_close()',source)
        self.assertIn('widget.request_close(lambda w=widget:',source)


if __name__=='__main__':unittest.main()
