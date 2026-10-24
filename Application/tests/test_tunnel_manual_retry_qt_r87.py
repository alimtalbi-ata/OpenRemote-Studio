"""R87: Qt SSH manual retry and fail-closed lifecycle tests.

No real network, secrets, or host-key acceptance. Author: Abdelhalim Talbi.
"""
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from ssh_tunnel_qt import SSHTunnelPanel
    from tunnel_controller import TunnelSnapshot
except ImportError:
    QApplication = None


class FakeController:
    def __init__(self):
        self.phase = 'idle'
        self.calls = []
        self.stops = 0

    def start(self, settings, **kwargs):
        self.calls.append(kwargs)
        self.phase = 'active'

    def stop(self):
        self.stops += 1
        self.phase = 'closed'

    def poll(self):
        return TunnelSnapshot(self.phase)

    def is_shutdown_complete(self):
        return self.phase in ('idle', 'closed', 'failed', 'disconnected')


@unittest.skipIf(QApplication is None, 'PySide6 unavailable; Windows CI required')
class QtManualRetryR87(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self):
        panel = SSHTunnelPanel(
            {'protocol': 'SSH', 'host': 'example.test', 'user': 'operator'},
            controller_factory=FakeController)
        panel.key_file.setText('synthetic-not-a-key')
        panel.consent.setChecked(True)
        self.addCleanup(panel.close)
        self.addCleanup(panel._timer.stop)
        return panel

    def test_failed_connection_requires_manual_retry_and_fresh_consent(self):
        panel = self.panel()
        first = panel._controller
        panel.start_tunnel()
        self.assertEqual(len(first.calls), 1)
        first.phase = 'failed'
        panel._refresh()
        self.assertTrue(panel.retry_button.isEnabled())
        self.assertFalse(panel.start_button.isEnabled())
        self.assertEqual(len(first.calls), 1)  # no automatic reconnect

        self.assertTrue(panel.prepare_retry())
        self.assertIsNot(panel._controller, first)
        self.assertFalse(panel.consent.isChecked())
        self.assertTrue(panel.consent.isEnabled())
        self.assertFalse(panel.host.isReadOnly())
        self.assertFalse(panel.keepalive_seconds.isReadOnly())
        self.assertTrue(panel.start_button.isEnabled())
        self.assertFalse(panel.retry_button.isEnabled())

        panel.start_tunnel()
        self.assertEqual(panel._controller.calls, [])
        self.assertIn('autorisation', panel.status.text())
        panel.consent.setChecked(True)
        panel.start_tunnel()
        self.assertEqual(len(panel._controller.calls), 1)
        self.assertEqual(len(first.calls), 1)

    def test_retry_is_blocked_until_cleanup_is_complete(self):
        panel = self.panel()
        panel.start_tunnel()
        original = panel._controller
        original.phase = 'cleanup'
        panel._refresh()
        self.assertFalse(panel.retry_button.isEnabled())
        self.assertFalse(panel.prepare_retry())
        self.assertIs(panel._controller, original)
        original.phase = 'disconnected'
        panel._refresh()
        self.assertTrue(panel.retry_button.isEnabled())
        self.assertTrue(panel.prepare_retry())

    def test_manual_stop_can_reset_without_reusing_closed_controller(self):
        panel = self.panel()
        panel.start_tunnel()
        old = panel._controller
        self.assertTrue(panel.request_close())
        self.assertEqual(old.stops, 1)
        self.assertTrue(panel.retry_button.isEnabled())
        self.assertTrue(panel.prepare_retry())
        self.assertIsNot(panel._controller, old)
        self.assertEqual(old.stops, 1)
        self.assertFalse(panel.consent.isChecked())

    def test_parent_close_callback_prevents_retry_even_after_cleanup(self):
        panel = self.panel()
        panel.start_tunnel()
        panel.request_close(lambda: None)
        self.assertTrue(panel._closing_panel)
        self.assertFalse(panel.retry_button.isEnabled())
        self.assertFalse(panel.prepare_retry())
        self.assertFalse(panel.start_button.isEnabled())


if __name__ == '__main__':
    unittest.main()
