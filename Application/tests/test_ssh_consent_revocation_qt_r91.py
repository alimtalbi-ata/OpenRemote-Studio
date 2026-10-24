"""R91: consent withdrawal always revokes live SSH, including Qt programmatic edits.
Author: Abdelhalim Talbi. No network, no credentials.
"""
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from ssh_tunnel_qt import SSHTunnelPanel
    from tunnel_controller import TunnelSnapshot
except ImportError:
    QApplication = None


class RecordingController:
    def __init__(self):
        self.phase = 'idle'
        self.starts = 0
        self.stops = 0

    def start(self, settings, **kwargs):
        self.starts += 1
        self.phase = 'connecting'

    def stop(self):
        self.stops += 1
        self.phase = 'closed'

    def poll(self):
        return TunnelSnapshot(self.phase)

    def is_shutdown_complete(self):
        return self.phase in ('idle', 'closed', 'failed', 'disconnected')


@unittest.skipIf(QApplication is None, 'PySide6 unavailable; run in Windows CI')
class ConsentRevocationR91(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = SSHTunnelPanel(controller_factory=RecordingController)
        self.panel.host.setText('example.test')
        self.panel.user.setText('operator')
        self.panel.key_file.setText('synthetic-key-path')
        self.addCleanup(self.panel._timer.stop)
        self.addCleanup(self.panel.close)

    def connect(self):
        self.panel.consent.setChecked(True)
        self.panel.start_tunnel()
        self.assertEqual(self.panel._controller.starts, 1)

    def test_explicit_consent_withdrawal_during_connection_revokes(self):
        self.connect()
        c = self.panel._controller
        self.assertEqual(c.phase, 'connecting')
        self.panel.consent.setChecked(False)
        self.assertEqual(c.stops, 1)
        self.assertEqual(c.phase, 'closed')
        self.assertFalse(self.panel._consent_guard.approved)

    def test_active_consent_withdrawal_revokes(self):
        self.connect()
        c = self.panel._controller
        c.phase = 'active'
        self.panel.consent.setChecked(False)
        self.assertEqual(c.stops, 1)
        self.assertFalse(self.panel._consent_guard.approved)
        self.panel.start_tunnel()
        self.assertEqual(c.starts, 1)

    def test_edit_after_uncheck_still_revokes_live_tunnel(self):
        self.connect()
        c = self.panel._controller
        self.panel.consent.blockSignals(True)
        self.panel.consent.setChecked(False)
        self.panel.consent.blockSignals(False)
        c.phase = 'active'
        self.panel.target_host.setText('other.example.test')
        self.assertEqual(c.stops, 1)
        self.assertFalse(self.panel._consent_guard.approved)

    def test_offline_consent_withdrawal_never_opens_or_stops_network(self):
        c = self.panel._controller
        self.panel.consent.setChecked(True)
        self.panel.consent.setChecked(False)
        self.assertEqual((c.starts, c.stops), (0, 0))
        self.panel.start_tunnel()
        self.assertEqual(c.starts, 0)

    def test_edit_while_checked_stops_exactly_once(self):
        self.connect()
        c = self.panel._controller
        c.phase = 'active'
        self.panel.key_file.setText('different-synthetic-key')
        self.assertEqual(c.stops, 1)
        self.assertFalse(self.panel.consent.isChecked())


if __name__ == '__main__':
    unittest.main()
