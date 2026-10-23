"""Qt headless: opt-in, offline state, fake remote data, no real network."""
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from netbox_preview_qt import NetBoxPreviewPanel
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, 'PySide6 unavailable: run Qt tests on Windows CI')
class NetBoxPreviewQtR74Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_offline_default_no_transport(self):
        def fail(*args):
            raise AssertionError('No network allowed before consent')
        pane = NetBoxPreviewPanel([{'host': 'server.example', 'protocol': 'SSH'}], client_factory=fail)
        self.assertFalse(pane.online.isChecked())
        pane.refresh()
        self.assertIn('Hors ligne', pane.status.text())
        self.assertEqual(pane.table.topLevelItemCount(), 0)
        pane.close()

    def test_explicit_online_uses_fake_client_and_displays_diff(self):
        calls = []
        class Fake:
            def __init__(self, origin, token):
                calls.append((origin, token))
            def devices(self, *, online):
                if not online:
                    raise AssertionError('online expected')
                return {'state': 'ok', 'devices': [{'id': 1, 'name': 'server.example'}]}
        pane = NetBoxPreviewPanel([{'host': 'server.example', 'protocol': 'SSH', 'user': 'secret'}],
                                  client_factory=Fake)
        pane.origin.setText('https://example.test')
        pane.online.setChecked(True)
        pane.refresh()
        for _ in range(100):
            self.app.processEvents()
            if pane.refresh_button.isEnabled():
                break
            QTest.qWait(10)
        self.assertTrue(pane.refresh_button.isEnabled())
        self.assertEqual(pane.table.topLevelItemCount(), 1)
        self.assertEqual(pane.table.topLevelItem(0).text(0), 'matched')
        self.assertNotIn('secret', pane.status.text())
        self.assertEqual(calls[0][0], 'https://example.test')
        pane.close()


if __name__ == '__main__':
    unittest.main()
