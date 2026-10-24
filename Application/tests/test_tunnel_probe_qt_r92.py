"""R92 Qt opt-in active probe, synthetic controller, no SSH traffic.
Author: Abdelhalim Talbi.
"""
import unittest
try:
    from PySide6.QtWidgets import QApplication
    from ssh_tunnel_qt import SSHTunnelPanel
    from tunnel_controller import TunnelSnapshot
except ImportError:
    QApplication = None


class Recorder:
    def __init__(self):
        self.calls = []
        self.stops = 0

    def start(self, settings, **kwargs):
        if not 0 <= kwargs['probe_interval_seconds'] <= 300:
            raise ValueError('invalid SSH probe interval')
        if not 1 <= kwargs['probe_timeout_seconds'] <= 30:
            raise ValueError('invalid SSH probe timeout')
        self.calls.append(kwargs)

    def stop(self):
        self.stops += 1

    def poll(self):
        return TunnelSnapshot('active' if self.calls else 'idle')

    def is_shutdown_complete(self):
        return False


@unittest.skipIf(QApplication is None, 'PySide6 unavailable; Windows CI required')
class R92QtProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_panel(self):
        panel = SSHTunnelPanel({'protocol': 'SSH', 'host': 'example.test', 'user': 'operator'},
                               controller_factory=Recorder)
        panel.key_file.setText('synthetic-key-path')
        panel.consent.setChecked(True)
        self.addCleanup(panel._timer.stop)
        self.addCleanup(panel.close)
        return panel

    def test_disabled_by_default_and_forwarded(self):
        panel = self.make_panel()
        panel.start_tunnel()
        self.assertEqual(panel._controller.calls[0]['probe_interval_seconds'], 0)
        self.assertEqual(panel._controller.calls[0]['probe_timeout_seconds'], 5)

    def test_opt_in_requires_fresh_approval_and_locks_fields(self):
        panel = self.make_panel()
        panel.probe_interval_seconds.setText('15')
        panel.probe_timeout_seconds.setText('4')
        self.assertFalse(panel.consent.isChecked())
        panel.start_tunnel()
        self.assertEqual(panel._controller.calls, [])
        panel.consent.setChecked(True)
        panel.start_tunnel()
        self.assertEqual(panel._controller.calls[0]['probe_interval_seconds'], 15)
        self.assertEqual(panel._controller.calls[0]['probe_timeout_seconds'], 4)
        self.assertTrue(panel.probe_interval_seconds.isReadOnly())
        self.assertTrue(panel.probe_timeout_seconds.isReadOnly())

    def test_invalid_values_do_not_activate_controller(self):
        for field, bad in [('probe_interval_seconds', '301'), ('probe_timeout_seconds', '0'),
                           ('probe_timeout_seconds', 'abc')]:
            with self.subTest(field=field, bad=bad):
                panel = self.make_panel()
                getattr(panel, field).setText(bad)
                panel.consent.setChecked(True)
                panel.start_tunnel()
                self.assertEqual(panel._controller.calls, [])
                self.assertIn('Configuration refusée', panel.status.text())


if __name__ == '__main__':
    unittest.main()
