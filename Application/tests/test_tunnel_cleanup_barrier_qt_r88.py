"""R88 Qt SSH cleanup barrier regression (synthetic controller only).

Author: Abdelhalim Talbi. No network or credentials are used.
"""
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from ssh_tunnel_qt import SSHTunnelPanel
    from tunnel_controller import TunnelSnapshot
except ImportError:
    QApplication = None


class SlowCleanupController:
    def __init__(self):
        self.phase = 'idle'
        self.drained = False
        self.stops = 0

    def start(self, settings, **kwargs):
        self.phase = 'active'

    def stop(self):
        self.stops += 1
        self.phase = 'closed'

    def poll(self):
        return TunnelSnapshot(self.phase)

    def is_shutdown_complete(self):
        return self.phase == 'idle' or (self.phase in
            ('closed', 'failed', 'disconnected') and self.drained)


@unittest.skipIf(QApplication is None, 'PySide6 required; run in Windows CI')
class QtCleanupBarrierR88(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self):
        panel = SSHTunnelPanel(controller_factory=SlowCleanupController)
        self.addCleanup(panel._timer.stop)
        self.addCleanup(panel.close)
        return panel

    def test_parent_close_callback_waits_for_confirmed_drain(self):
        panel = self.panel()
        panel._controller.phase = 'active'
        fired = []
        self.assertFalse(panel.request_close(lambda: fired.append('closed')))
        self.app.processEvents()
        self.assertEqual(fired, [])
        self.assertTrue(panel._timer.isActive())
        self.assertFalse(panel.retry_button.isEnabled())
        self.assertIn('Nettoyage', panel.status.text())
        panel._controller.drained = True
        panel._refresh()
        self.app.processEvents()
        self.assertEqual(fired, ['closed'])
        self.assertFalse(panel._timer.isActive())

    def test_failed_phase_does_not_enable_retry_before_drain(self):
        panel = self.panel()
        panel._controller.phase = 'failed'
        panel._refresh()
        self.assertFalse(panel.retry_button.isEnabled())
        self.assertFalse(panel.prepare_retry())
        self.assertTrue(panel._timer.isActive())
        panel._controller.drained = True
        panel._refresh()
        self.assertTrue(panel.retry_button.isEnabled())
        self.assertTrue(panel.prepare_retry())
        self.assertFalse(panel.consent.isChecked())

    def test_callback_is_dispatched_only_once(self):
        panel = self.panel()
        panel._controller.phase = 'active'
        fired = []
        panel.request_close(lambda: fired.append(1))
        for _ in range(3):
            panel._refresh()
            self.app.processEvents()
        self.assertEqual(fired, [])
        panel._controller.drained = True
        for _ in range(3):
            panel._refresh()
            self.app.processEvents()
        self.assertEqual(fired, [1])


if __name__ == '__main__':
    unittest.main()
