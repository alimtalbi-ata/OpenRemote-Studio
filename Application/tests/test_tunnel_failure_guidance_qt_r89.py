"""R89: redacted Qt SSH failure guidance. Author: Abdelhalim Talbi."""
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from ssh_tunnel_qt import SSHTunnelPanel
    from tunnel_controller import TunnelSnapshot
except ImportError:
    QApplication = None


class FailureController:
    def __init__(self):
        self.snapshot = TunnelSnapshot('failed', failure_code='host_key')

    def poll(self):
        return self.snapshot

    def is_shutdown_complete(self):
        return True

    def stop(self):
        pass


@unittest.skipIf(QApplication is None, 'PySide6 unavailable')
class QtSSHFailureGuidanceR89(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = SSHTunnelPanel(controller_factory=FailureController)
        self.addCleanup(self.panel._timer.stop)
        self.addCleanup(self.panel.close)

    def test_host_key_error_is_actionable_and_redacted(self):
        self.panel._refresh()
        text = self.panel.status.text()
        self.assertIn('known_hosts', text)
        self.assertNotIn('example.test', text)
        self.assertTrue(self.panel.retry_button.isEnabled())

    def test_authentication_error_is_actionable_and_redacted(self):
        self.panel._controller.snapshot = TunnelSnapshot(
            'failed', failure_code='authentication')
        self.panel._refresh()
        self.assertIn('Authentification SSH refusée', self.panel.status.text())
        self.assertNotIn('known_hosts', self.panel.status.text())

    def test_generic_error_does_not_show_exception_details(self):
        self.panel._controller.snapshot = TunnelSnapshot(
            'failed', failure_code='generic')
        self.panel._refresh()
        self.assertIn('détails sensibles masqués', self.panel.status.text())
        self.assertNotIn('example.test', self.panel.status.text())

    def test_cleanup_barrier_overrides_actionable_failure_message(self):
        self.panel._controller.snapshot = TunnelSnapshot(
            'cleanup', failure_code='host_key')
        self.panel._refresh()
        self.assertFalse(self.panel.retry_button.isEnabled())
        self.assertIn('Nettoyage', self.panel.status.text())


if __name__ == '__main__':
    unittest.main()
