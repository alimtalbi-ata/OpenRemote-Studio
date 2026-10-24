"""R90: Qt SSH consent is bound to form revision; no network used.
Author: Abdelhalim Talbi.
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
        self.calls.append((settings, kwargs))
        self.phase = 'active'

    def stop(self):
        self.stops += 1
        self.phase = 'closed'

    def poll(self):
        return TunnelSnapshot(self.phase)

    def is_shutdown_complete(self):
        return self.phase in ('idle', 'closed', 'failed', 'disconnected')


@unittest.skipIf(QApplication is None, 'PySide6 unavailable; run Windows Qt CI')
class QtConsentR90(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = SSHTunnelPanel(controller_factory=FakeController)
        self.panel.host.setText('example.test')
        self.panel.user.setText('operator')
        self.panel.key_file.setText('synthetic-path')
        self.addCleanup(self.panel._timer.stop)
        self.addCleanup(self.panel.close)

    def test_host_change_revokes_consent_before_any_connection(self):
        p = self.panel
        p.consent.setChecked(True)
        p.host.setText('changed.example.test')
        self.assertFalse(p.consent.isChecked())
        p.start_tunnel()
        self.assertEqual(p._controller.calls, [])
        self.assertIn('autorisation', p.status.text())

    def test_key_and_known_hosts_changes_each_require_new_approval(self):
        p = self.panel
        for field, value in ((p.key_file, 'new-private-key'),
                             (p.known_hosts, 'new-known-hosts')):
            p.consent.setChecked(True)
            field.setText(value)
            self.assertFalse(p.consent.isChecked())
            self.assertFalse(p._consent_guard.approved)
        p.consent.setChecked(True)
        p.start_tunnel()
        self.assertEqual(len(p._controller.calls), 1)

    def test_active_programmatic_edit_revokes_existing_tunnel(self):
        p = self.panel
        p.consent.setChecked(True)
        p.start_tunnel()
        original = p._controller
        self.assertEqual(original.phase, 'active')
        p.target_port.setText('443')  # even if QLineEdit is read-only
        self.assertFalse(p.consent.isChecked())
        self.assertEqual(original.stops, 1)
        self.assertEqual(original.phase, 'closed')

    def test_manual_retry_never_restores_prior_consent(self):
        p = self.panel
        p.consent.setChecked(True)
        p.start_tunnel()
        p.request_close()
        self.assertTrue(p.prepare_retry())
        self.assertFalse(p.consent.isChecked())
        self.assertFalse(p._consent_guard.approved)
        p.start_tunnel()
        self.assertEqual(p._controller.calls, [])


if __name__ == '__main__':
    unittest.main()
