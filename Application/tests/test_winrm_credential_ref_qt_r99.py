"""R99 Qt WinCred flow with synthetic transport; no real WinRM server."""
import threading
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from winrm_inventory_qt import WinRMInventoryPanel
except ImportError:
    QApplication = None


def wait_until(app, predicate):
    for _ in range(300):
        app.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


@unittest.skipIf(QApplication is None, 'PySide6 unavailable; Windows Qt CI required')
class WinRMCredentialReferenceQtR99Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self, resolver, factory):
        pane = WinRMInventoryPanel(credential_resolver=resolver, client_factory=factory,
                                   credential_provider=lambda: self.fail('plaintext prompt must not run'))
        pane.origin.setText('https://win.example.test')
        pane.username.setText('readonly')
        pane.credential_ref.setText('wincred:OpenRemote/WinRM/lab')
        return pane

    def test_offline_does_not_resolve_or_connect(self):
        calls = []
        def forbidden(*args, **kwargs):
            calls.append('unexpected')
            raise AssertionError('offline')
        pane = self.panel(forbidden, forbidden)
        try:
            pane.refresh()
            self.assertEqual(calls, [])
            self.assertFalse(pane.consent.isChecked())
        finally:
            pane.close()

    def test_reference_resolves_in_worker_and_is_not_displayed_as_secret(self):
        secret = 'TEST_ONLY_SECRET_R99'
        main_thread = threading.get_ident()
        calls = []
        def resolver(target):
            calls.append(('resolve', target, threading.get_ident()))
            return secret
        class Fake:
            def __init__(self, origin, username, credential_provider):
                calls.append(('init', origin, username))
                self.credential_provider = credential_provider
            def inventory(self, *, online, cancelled):
                calls.append(('query', self.credential_provider()))
                return {'state': 'ok', 'read_only': True,
                        'os': {'caption': 'Windows', 'version': '10', 'build': '1', 'computer': 'LAB'},
                        'disks': []}
        pane = self.panel(resolver, Fake)
        try:
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))
            self.assertEqual(pane.table.topLevelItemCount(), 4)
            self.assertEqual(calls[0][1], 'OpenRemote/WinRM/lab')
            self.assertNotEqual(calls[0][2], main_thread)
            self.assertEqual(calls[2], ('query', secret))
            rendered = pane.status.text() + ''.join(
                pane.table.topLevelItem(i).text(1) for i in range(pane.table.topLevelItemCount()))
            self.assertNotIn(secret, rendered)
            self.assertIsNone(pane._pending)
        finally:
            pane.close()

    def test_reference_change_revokes_consent_and_blocks_network(self):
        calls = []
        pane = self.panel(lambda _: calls.append('secret') or 'secret',
                          lambda *a, **kw: calls.append('network'))
        try:
            pane.consent.setChecked(True)
            pane.credential_ref.setText('wincred:other')
            self.assertFalse(pane.consent.isChecked())
            pane.refresh()
            self.assertEqual(calls, [])
            self.assertIn('Hors ligne', pane.status.text())
        finally:
            pane.close()

    def test_invalid_reference_does_not_resolve_or_connect(self):
        calls = []
        pane = self.panel(lambda _: calls.append('secret'), lambda *a, **kw: calls.append('network'))
        try:
            pane.credential_ref.setText('wincred:bad?target')
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertEqual(calls, [])
            self.assertIn('Référence', pane.status.text())
        finally:
            pane.close()

    def test_resolver_failure_redacted_and_no_transport(self):
        secret = 'SENSITIVE_R99'
        calls = []
        def fail(_):
            raise RuntimeError('failed ' + secret)
        pane = self.panel(fail, lambda *a, **kw: calls.append('network'))
        try:
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))
            self.assertEqual(calls, [])
            self.assertIn('winrm_credentials_unavailable', pane.status.text())
            self.assertNotIn(secret, pane.status.text())
        finally:
            pane.close()


if __name__ == '__main__':
    unittest.main()
