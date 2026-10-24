"""R83 Qt disconnect display and callback, with a fake controller only.
Author: Abdelhalim Talbi.
"""
import unittest
try:
    from PySide6.QtWidgets import QApplication
    from ssh_tunnel_qt import SSHTunnelPanel
except ImportError:
    QApplication = None


class Controller:
    def __init__(self):
        self.phase = 'active'
        self.stops = 0
    def poll(self):
        from tunnel_controller import TunnelSnapshot
        return TunnelSnapshot(self.phase)
    def is_shutdown_complete(self):
        return self.phase == 'disconnected'
    def stop(self):
        self.stops += 1


@unittest.skipIf(QApplication is None, 'PySide6 unavailable; execute in Windows CI')
class QtTunnelHealthR83(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_disconnect_is_explicit_and_triggers_pending_close_callback(self):
        panel = SSHTunnelPanel(controller_factory=Controller)
        panel._timer.start()
        called = []
        panel.request_close(lambda: called.append(True))
        self.assertEqual(panel._controller.stops, 1)
        panel._controller.phase = 'disconnected'
        panel._refresh()
        self.app.processEvents()
        self.assertIn('interrompue', panel.status.text())
        self.assertEqual(called, [True])
        self.assertFalse(panel._timer.isActive())
        panel.close()


if __name__ == '__main__':
    unittest.main()
