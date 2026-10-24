"""R94 Qt WinRM preview: explicit consent, redaction, stale results and offline safety.

Synthetic transport only; no real Windows Server or network.
Author: Abdelhalim Talbi.
"""
import threading
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from winrm_inventory_qt import WinRMInventoryPanel
except ImportError:
    QApplication = None


def wait_until(app, predicate, ticks=200):
    for _ in range(ticks):
        app.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


@unittest.skipIf(QApplication is None, 'PySide6 unavailable: Windows Qt CI required')
class WinRMInventoryQtR94Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_offline_default_does_not_resolve_credentials_or_network(self):
        calls = []
        def forbidden(*args, **kwargs):
            calls.append('called')
            raise AssertionError('No calls permitted offline')
        pane = WinRMInventoryPanel(client_factory=forbidden,
                                   credential_provider=forbidden)
        try:
            self.assertFalse(pane.consent.isChecked())
            pane.refresh()
            self.assertEqual(calls, [])
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertIn('Hors ligne', pane.status.text())
        finally:
            pane.close()

    def test_invalid_https_origin_does_not_ask_for_secret(self):
        calls = []
        pane = WinRMInventoryPanel(credential_provider=lambda: calls.append(1) or 'secret')
        try:
            pane.origin.setText('http://untrusted.example.test')
            pane.username.setText('reader')
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertEqual(calls, [])
            self.assertIn('winrm_invalid_https_origin', pane.status.text())
        finally:
            pane.close()

    def test_successful_read_only_inventory_is_sanitized(self):
        calls = []
        secret = 'NEVER_DISPLAY_ME_R94'
        class Fake:
            def __init__(self, origin, username, credential_provider):
                calls.append((origin, username))
                self.secret = credential_provider
            def inventory(self, *, online, cancelled):
                self_test.assertTrue(online)
                self_test.assertEqual(self.secret(), secret)
                return {'state': 'ok', 'read_only': True,
                        'os': {'caption': 'Windows Server', 'version': '10.0',
                               'build': '20348', 'computer': 'LAB-SRV'},
                        'disks': [{'drive': 'C:', 'size_bytes': 100, 'free_bytes': 20}]}
        self_test = self
        pane = WinRMInventoryPanel(client_factory=Fake,
                                   credential_provider=lambda: secret)
        try:
            pane.origin.setText('https://lab.example.test')
            pane.username.setText('reader')
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))
            self.assertEqual(pane.table.topLevelItemCount(), 5)
            self.assertEqual(calls, [('https://lab.example.test', 'reader')])
            displayed = pane.status.text() + ''.join(
                pane.table.topLevelItem(i).text(1)
                for i in range(pane.table.topLevelItemCount()))
            self.assertNotIn(secret, displayed)
        finally:
            pane.close()

    def test_revocation_discards_stale_result(self):
        entered, release = threading.Event(), threading.Event()
        class Fake:
            def __init__(self, origin, username, credential_provider):
                self.password = credential_provider
            def inventory(self, *, online, cancelled):
                entered.set()
                release.wait(2)
                return {'state': 'ok', 'read_only': True,
                        'os': {'caption': 'Old result', 'version': '10',
                               'build': '1', 'computer': 'STALE'},
                        'disks': []}
        pane = WinRMInventoryPanel(client_factory=Fake,
                                   credential_provider=lambda: 'ephemeral')
        try:
            pane.origin.setText('https://lab.example.test')
            pane.username.setText('reader')
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(entered.wait(2))
            pane.consent.setChecked(False)
            release.set()
            self.assertTrue(pane._pool.waitForDone(4000))
            self.app.processEvents()
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertIn('Hors ligne', pane.status.text())
        finally:
            release.set()
            pane.close()

    def test_transport_exception_cannot_expose_secret(self):
        secret = 'R94_SENSITIVE_CREDENTIAL'
        class Fake:
            def __init__(self, origin, username, credential_provider):
                self.password = credential_provider
            def inventory(self, *, online, cancelled):
                raise RuntimeError('danger ' + self.password())
        pane = WinRMInventoryPanel(client_factory=Fake,
                                   credential_provider=lambda: secret)
        try:
            pane.origin.setText('https://lab.example.test')
            pane.username.setText('reader')
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))
            self.assertIn('winrm_transport_unavailable', pane.status.text())
            self.assertNotIn(secret, pane.status.text())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
        finally:
            pane.close()


if __name__ == '__main__':
    unittest.main()
