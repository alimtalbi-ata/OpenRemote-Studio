"""R96 Qt WinRM services: local filtering, offline default, stale reply and redaction.

Synthetic transport only. No WinRM server or production side effects.
Author: Abdelhalim Talbi.
"""
import threading
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from winrm_inventory_qt import WinRMServicesPanel, WinRMInventoryPanel
except ImportError:
    QApplication = None


def wait_until(app, predicate, ticks=300):
    for _ in range(ticks):
        app.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


def services_result(items, truncated=False):
    return {'state': 'ok', 'read_only': True, 'limit': 128,
            'may_be_truncated': truncated, 'services': items}


def item(name, state='Running', mode='Auto'):
    return {'name': name, 'display_name': name + ' Service',
            'state': state, 'start_mode': mode}


@unittest.skipIf(QApplication is None, 'PySide6 unavailable: Windows Qt CI required')
class ServicesQtR96Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self, factory, secret='EPHEMERAL-R96'):
        panel = WinRMServicesPanel(client_factory=factory,
                                  credential_provider=lambda: secret)
        panel.origin.setText('https://windows.example.test:5986')
        panel.username.setText('reader')
        return panel

    def test_offline_default_never_requests_credentials_or_network(self):
        calls = []
        def forbidden(*args, **kwargs):
            calls.append(1)
            raise AssertionError('must remain offline')
        panel = WinRMServicesPanel(client_factory=forbidden,
                                  credential_provider=forbidden)
        try:
            panel.refresh()
            panel.service_filter.setText('running')
            self.assertEqual(calls, [])
            self.assertEqual(panel.table.topLevelItemCount(), 0)
            self.assertFalse(panel.consent.isChecked())
        finally:
            panel.close()

    def test_successful_filter_is_local_and_does_not_repeat_winrm_post(self):
        calls = []
        class Fake:
            def __init__(self, origin, username, credential_provider):
                self.provider = credential_provider
            def services(self, *, online, cancelled):
                calls.append((online, self.provider()))
                return services_result([item('Spooler', 'Stopped', 'Manual'),
                                        item('W32Time', 'Running', 'Auto')])
        panel = self.panel(Fake)
        try:
            panel.consent.setChecked(True)
            panel.refresh()
            self.assertTrue(wait_until(self.app, lambda: panel.refresh_button.isEnabled()))
            self.assertEqual(panel.table.topLevelItemCount(), 2)
            panel.service_filter.setText('stopped')
            self.assertEqual(panel.table.topLevelItemCount(), 1)
            self.assertEqual(panel.table.topLevelItem(0).text(0), 'Spooler')
            panel.service_filter.setText('w32')
            self.assertEqual(panel.table.topLevelItem(0).text(0), 'W32Time')
            panel.service_filter.clear()
            self.assertEqual(panel.table.topLevelItemCount(), 2)
            self.assertEqual(calls, [(True, 'EPHEMERAL-R96')])
            self.assertNotIn('EPHEMERAL-R96', panel.status.text() +
                             panel.filter_status.text())
        finally:
            panel.close()

    def test_truncation_is_explicit(self):
        class Fake:
            def __init__(self, *args, **kwargs):
                pass
            def services(self, *, online, cancelled):
                return services_result([item('Spooler')], truncated=True)
        panel = self.panel(Fake)
        try:
            panel.consent.setChecked(True)
            panel.refresh()
            self.assertTrue(wait_until(self.app, lambda: panel.refresh_button.isEnabled()))
            self.assertIn('tronqué', panel.status.text())
            self.assertEqual(panel.table.topLevelItemCount(), 1)
        finally:
            panel.close()

    def test_revocation_discards_stale_and_prevents_concurrent_post(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        class Fake:
            def __init__(self, *args, **kwargs):
                pass
            def services(self, *, online, cancelled):
                calls.append(1)
                entered.set()
                release.wait(3)
                return services_result([item('STALE')])
        panel = self.panel(Fake)
        try:
            panel.consent.setChecked(True)
            panel.refresh()
            self.assertTrue(entered.wait(3))
            panel.consent.setChecked(False)
            panel.consent.setChecked(True)
            panel.refresh()
            self.assertEqual(calls, [1])
            self.assertFalse(panel.refresh_button.isEnabled())
            release.set()
            self.assertTrue(wait_until(self.app, lambda: panel.refresh_button.isEnabled()))
            self.assertEqual(panel.table.topLevelItemCount(), 0)
            self.assertIn('Hors ligne', panel.status.text())
        finally:
            release.set()
            panel.close()

    def test_transport_exception_redacted(self):
        secret = 'NEVER_LEAK_R96'
        class Fake:
            def __init__(self, origin, username, credential_provider):
                self.provider = credential_provider
            def services(self, *, online, cancelled):
                raise RuntimeError('provider failed: ' + self.provider())
        panel = self.panel(Fake, secret)
        try:
            panel.consent.setChecked(True)
            panel.refresh()
            self.assertTrue(wait_until(self.app, lambda: panel.refresh_button.isEnabled()))
            self.assertIn('winrm_transport_unavailable', panel.status.text())
            self.assertNotIn(secret, panel.status.text())
            self.assertEqual(panel.table.topLevelItemCount(), 0)
        finally:
            panel.close()

    def test_malformed_service_never_reaches_ui(self):
        class Fake:
            def __init__(self, *args, **kwargs):
                pass
            def services(self, *, online, cancelled):
                return services_result([item('bad' + chr(10) + 'control')])
        panel = self.panel(Fake)
        try:
            panel.consent.setChecked(True)
            panel.refresh()
            self.assertTrue(wait_until(self.app, lambda: panel.refresh_button.isEnabled()))
            self.assertIn('invalide', panel.status.text())
            self.assertEqual(panel.table.topLevelItemCount(), 0)
        finally:
            panel.close()

    def test_empty_display_name_from_backend_is_supported(self):
        class Fake:
            def __init__(self, *args, **kwargs):
                pass
            def services(self, *, online, cancelled):
                return services_result([{'name': 'W32Time', 'display_name': '',
                                         'state': 'Running', 'start_mode': 'Auto'}])
        panel = self.panel(Fake)
        try:
            panel.consent.setChecked(True)
            panel.refresh()
            self.assertTrue(wait_until(self.app, lambda: panel.refresh_button.isEnabled()))
            self.assertEqual(panel.table.topLevelItemCount(), 1)
            self.assertEqual(panel.table.topLevelItem(0).text(1), '')
        finally:
            panel.close()

    def test_unsupported_operation_rejected(self):
        with self.assertRaises(ValueError):
            WinRMInventoryPanel(mode='arbitrary-script')


if __name__ == '__main__':
    unittest.main()
