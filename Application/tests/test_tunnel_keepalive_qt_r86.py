"""R86 Qt SSH keepalive contract, no live SSH traffic. Author: Abdelhalim Talbi."""
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from ssh_tunnel_qt import SSHTunnelPanel
    from tunnel_controller import TunnelSnapshot
except ImportError:
    QApplication = None


class RecordingController:
    def __init__(self):
        self.calls = []
        self.stops = 0

    def start(self, settings, **kwargs):
        if not 0 <= kwargs['keepalive_seconds'] <= 300:
            raise ValueError('invalid SSH keepalive interval')
        self.calls.append((settings, kwargs))

    def stop(self):
        self.stops += 1

    def poll(self):
        return TunnelSnapshot('active' if self.calls else 'idle')

    def is_shutdown_complete(self):
        return False


@unittest.skipIf(QApplication is None, 'PySide6 unavailable; Windows CI required')
class QtKeepaliveR86(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_panel(self):
        panel = SSHTunnelPanel(
            {'protocol': 'SSH', 'host': 'example.test', 'user': 'operator'},
            controller_factory=RecordingController)
        panel.key_file.setText('synthetic-key-path')
        panel.consent.setChecked(True)
        return panel

    def test_keepalive_off_by_default_and_forwarded(self):
        panel = self.make_panel()
        try:
            self.assertEqual(panel.keepalive_seconds.text(), '0')
            panel.start_tunnel()
            self.assertEqual(len(panel._controller.calls), 1)
            self.assertEqual(panel._controller.calls[0][1]['keepalive_seconds'], 0)
            self.assertTrue(panel.keepalive_seconds.isReadOnly())
            self.assertFalse(panel.start_button.isEnabled())
        finally:
            panel._timer.stop()
            panel.close()

    def test_opt_in_interval_forwarded_to_controller(self):
        panel = self.make_panel()
        try:
            panel.keepalive_seconds.setText('30')
            panel.consent.setChecked(True)  # R90: approve the edited configuration
            panel.start_tunnel()
            self.assertEqual(len(panel._controller.calls), 1)
            self.assertEqual(panel._controller.calls[0][1]['keepalive_seconds'], 30)
        finally:
            panel._timer.stop()
            panel.close()

    def test_invalid_interval_fails_before_controller_call(self):
        for invalid in ('-1', '301', 'abc', '', '1.5'):
            with self.subTest(value=invalid):
                panel = self.make_panel()
                try:
                    panel.keepalive_seconds.setText(invalid)
                    panel.consent.setChecked(True)  # isolate validation from consent guard
                    panel.start_tunnel()
                    self.assertEqual(panel._controller.calls, [])
                    self.assertIn('Configuration refusée', panel.status.text())
                    self.assertTrue(panel.start_button.isEnabled())
                finally:
                    panel._timer.stop()
                    panel.close()

    def test_consent_required_even_with_keepalive(self):
        panel = self.make_panel()
        try:
            panel.consent.setChecked(False)
            panel.keepalive_seconds.setText('30')
            panel.start_tunnel()
            self.assertEqual(panel._controller.calls, [])
            self.assertIn('autorisation', panel.status.text())
        finally:
            panel._timer.stop()
            panel.close()


if __name__ == '__main__':
    unittest.main()
