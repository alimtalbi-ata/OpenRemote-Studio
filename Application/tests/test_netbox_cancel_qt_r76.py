"""R76 headless Qt: consent/origin/close invalidate stale async results."""
import threading
import unittest
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from netbox_preview_qt import NetBoxPreviewPanel, _Fetch
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, 'PySide6 unavailable: Qt tests on Windows CI')
class NetBoxCancelQtR76Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait_until(self, predicate):
        for _ in range(250):
            self.app.processEvents()
            if predicate():
                return True
            QTest.qWait(10)
        return False

    def test_pre_cancelled_worker_never_constructs_client(self):
        calls = []
        worker = _Fetch(9, 'https://netbox.example', 'SECRET', [], lambda *_: calls.append(1))
        emitted = []
        worker.signals.finished.connect(lambda gen, data: emitted.append((gen, data)))
        worker.cancel()
        worker.run()
        self.assertEqual(calls, [])
        self.assertEqual(emitted, [(9, {'state': 'cancelled'})])
        self.assertEqual(worker.token, '')

    def test_revoke_consent_discards_inflight_data(self):
        started, release = threading.Event(), threading.Event()
        class Fake:
            def __init__(self, origin, token):
                pass
            def devices(self, *, online):
                started.set()
                release.wait(2)
                return {'state': 'ok', 'devices': [{'id': 1, 'name': 'private-host'}]}
        pane = NetBoxPreviewPanel([], client_factory=Fake)
        try:
            pane.origin.setText('https://netbox.example')
            pane.online.setChecked(True)
            pane.refresh()
            self.assertTrue(self.wait_until(started.is_set))
            pane.online.setChecked(False)
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertIn('Hors ligne', pane.status.text())
            release.set()
            self.assertTrue(self.wait_until(lambda: pane._pending is None))
            QTest.qWait(50); self.app.processEvents()
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertNotIn('private-host', pane.status.text())
        finally:
            release.set()
            pane.close()

    def test_origin_change_discards_old_result_not_new(self):
        started, release = threading.Event(), threading.Event()
        class Fake:
            def __init__(self, origin, token):
                self.origin = origin
            def devices(self, *, online):
                if self.origin.endswith('old.example'):
                    started.set()
                    release.wait(2)
                    return {'state': 'ok', 'devices': [{'id': 1, 'name': 'old-host'}]}
                return {'state': 'ok', 'devices': [{'id': 2, 'name': 'new-host'}]}
        pane = NetBoxPreviewPanel([], client_factory=Fake)
        try:
            pane.origin.setText('https://old.example')
            pane.online.setChecked(True)
            pane.refresh()
            self.assertTrue(self.wait_until(started.is_set))
            pane.origin.setText('https://new.example')
            pane.refresh()
            self.assertTrue(self.wait_until(lambda: pane.table.topLevelItemCount() == 1))
            self.assertEqual(pane.table.topLevelItem(0).text(1), 'new-host')
            release.set()
            QTest.qWait(50); self.app.processEvents()
            self.assertEqual(pane.table.topLevelItem(0).text(1), 'new-host')
        finally:
            release.set()
            pane.close()

    def test_close_discards_inflight_data(self):
        started, release = threading.Event(), threading.Event()
        class Fake:
            def __init__(self, origin, token):
                pass
            def devices(self, *, online):
                started.set(); release.wait(2)
                return {'state': 'ok', 'devices': [{'id': 1, 'name': 'late-host'}]}
        pane = NetBoxPreviewPanel([], client_factory=Fake)
        pane.origin.setText('https://netbox.example')
        pane.online.setChecked(True)
        pane.refresh()
        self.assertTrue(self.wait_until(started.is_set))
        pane.close()
        release.set()
        QTest.qWait(50); self.app.processEvents()
        self.assertEqual(pane.table.topLevelItemCount(), 0)
        self.assertFalse(pane.refresh_button.isEnabled())


if __name__ == '__main__':
    unittest.main()
