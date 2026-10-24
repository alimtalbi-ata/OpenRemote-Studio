"""R75 Qt headless: filtering is local and remains opt-in."""
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from netbox_preview_qt import NetBoxPreviewPanel
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, 'PySide6 unavailable: Qt tests on Windows CI')
class NetBoxFilterQtR75Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_offline_filter_never_calls_network(self):
        def forbidden(*args):
            raise AssertionError('No network without explicit consent')
        pane = NetBoxPreviewPanel([{'host': 'private.internal', 'protocol': 'SSH'}],
                                  client_factory=forbidden)
        pane.search_filter.setText('private')
        pane.status_filter.setCurrentIndex(3)
        pane.refresh()
        self.assertIn('Hors ligne', pane.status.text())
        self.assertEqual(pane.table.topLevelItemCount(), 0)
        pane.close()

    def test_filter_does_not_refetch_and_keeps_counts(self):
        calls = []
        class Fake:
            def __init__(self, origin, token):
                calls.append(origin)
            def devices(self, *, online):
                if not online:
                    raise AssertionError('Explicit online expected')
                return {'state': 'ok', 'devices': [
                    {'id': 1, 'name': 'srv-one'},
                    {'id': 2, 'name': 'srv-two'}]}
        pane = NetBoxPreviewPanel([{'host': 'srv-one', 'protocol': 'SSH'}], client_factory=Fake)
        pane.origin.setText('https://example.test')
        pane.online.setChecked(True)
        pane.refresh()
        for _ in range(200):
            self.app.processEvents()
            if pane.refresh_button.isEnabled():
                break
            QTest.qWait(10)
        self.assertTrue(pane.refresh_button.isEnabled())
        self.assertEqual(pane.table.topLevelItemCount(), 2)
        pane.search_filter.setText('srv-two')
        self.assertEqual(pane.table.topLevelItemCount(), 1)
        self.assertEqual(pane.table.topLevelItem(0).text(0), 'missing_local')
        pane.status_filter.setCurrentIndex(1)
        self.assertEqual(pane.table.topLevelItemCount(), 0)
        self.assertIn('visibles : 0/2', pane.status.text())
        self.assertEqual(calls, ['https://example.test'])
        pane.close()


if __name__ == '__main__':
    unittest.main()
