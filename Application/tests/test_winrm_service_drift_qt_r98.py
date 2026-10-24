"""R98 Qt service drift: two explicit reads, no extra network, no stale baseline.

Synthetic WinRM transport only; real Windows Server not exercised.
Author: Abdelhalim Talbi.
"""
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from winrm_inventory_qt import WinRMServicesPanel
except ImportError:
    QApplication = None


def row(name, state='Running', mode='Auto'):
    return {'name': name, 'display_name': name, 'state': state, 'start_mode': mode}


def result(rows, truncated=False):
    return {'state': 'ok', 'read_only': True, 'limit': 128,
            'services': rows, 'may_be_truncated': truncated}


def wait_until(app, predicate):
    for _ in range(300):
        app.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


@unittest.skipIf(QApplication is None, 'PySide6 unavailable; Windows Qt CI required')
class WinRMDriftQtR98Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self, replies):
        calls = []
        class Fake:
            def __init__(self, origin, username, credential_provider):
                self.provider = credential_provider
            def services(self, *, online, cancelled):
                calls.append(self.provider())
                return replies.pop(0)
        pane = WinRMServicesPanel(client_factory=Fake,
                                  credential_provider=lambda: 'TEST-SECRET-R98')
        pane.origin.setText('https://win.example.test')
        pane.username.setText('reader')
        return pane, calls

    def read(self, pane):
        pane.refresh()
        self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))

    def test_two_explicit_reads_show_transition_and_local_filter(self):
        pane, calls = self.panel([result([row('Spooler')]),
                                  result([row('Spooler', 'Stopped', 'Manual')])])
        try:
            pane.consent.setChecked(True)
            self.read(pane)
            self.assertIn('Première lecture', pane.drift_status.text())
            self.read(pane)
            self.assertIn('1 transition', pane.drift_status.text())
            self.assertIn('Running', pane.table.topLevelItem(0).text(4))
            self.assertIn('Stopped', pane.table.topLevelItem(0).text(4))
            pane.service_filter.setText('spool')
            self.assertEqual(len(calls), 2)
            self.assertNotIn('TEST-SECRET-R98', pane.drift_status.text())
        finally:
            pane.close()

    def test_consent_revocation_erases_baseline(self):
        pane, calls = self.panel([result([row('A')]), result([row('A', 'Stopped')])])
        try:
            pane.consent.setChecked(True)
            self.read(pane)
            pane.consent.setChecked(False)
            self.assertIsNone(pane._last_successful_services)
            pane.consent.setChecked(True)
            self.read(pane)
            self.assertIn('Première lecture', pane.drift_status.text())
            self.assertNotIn('Running', pane.table.topLevelItem(0).text(4))
        finally:
            pane.close()

    def test_truncated_inventory_does_not_infer_removed_services(self):
        pane, calls = self.panel([result([row('A')], True), result([row('B')], True)])
        try:
            pane.consent.setChecked(True)
            self.read(pane)
            self.read(pane)
            self.assertIn('non évalués', pane.drift_status.text())
            self.assertIn('0 disparition', pane.drift_status.text())
            self.assertEqual(len(calls), 2)
        finally:
            pane.close()

    def test_offline_never_requests_credentials_or_network(self):
        calls = []
        def forbidden(*args, **kwargs):
            calls.append(1)
            raise AssertionError('offline')
        pane = WinRMServicesPanel(client_factory=forbidden,
                                  credential_provider=forbidden)
        try:
            pane.refresh()
            self.assertEqual(calls, [])
            self.assertEqual(pane.table.topLevelItemCount(), 0)
        finally:
            pane.close()


if __name__ == '__main__':
    unittest.main()
