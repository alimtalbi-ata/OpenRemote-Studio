"""R110: the operator's Zabbix consent is bound to the edited HTTPS origin.
No real token or network is used. Qt execution is qualified in Windows CI.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import os
import threading
import unittest

try:
    from PySide6.QtCore import QThreadPool
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from zabbix_alerts_qt import ZabbixAlertsPanel
except ImportError:
    QThreadPool = QTest = QApplication = ZabbixAlertsPanel = None


TOKEN = "R110_FAKE_ZABBIX_TOKEN_MUST_NOT_BE_LOGGED"


def wait_until(app, predicate, ticks=300):
    for _ in range(ticks):
        app.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


def dashboard_snapshot(name="Synthetic active problem"):
    return {
        "state": "ok", "read_only": True,
        "problems": [{
            "event_id": "101", "name": name, "severity": 4,
            "severity_label": "Haute", "last_change": 1_790_000_000,
            "acknowledged": False, "hosts": [], "trigger_description": "Synthetic trigger",
        }],
        "limit": 10, "may_be_truncated": False,
    }


@unittest.skipIf(QApplication is None, "PySide6 unavailable: Qt tests run in Windows native CI")
class ZabbixConsentBindingR110Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_origin_change_revokes_consent_and_prevents_a_second_token_read(self):
        reads = []
        constructions = []

        class FakeClient:
            def __init__(self, origin, *, timeout, max_problems):
                constructions.append(origin)
            def problems(self, *, online, token, limit, cancelled):
                self_outer.assertTrue(online)
                self_outer.assertEqual(token, TOKEN)
                return dashboard_snapshot()

        self_outer = self
        pool = QThreadPool()
        pane = ZabbixAlertsPanel([], client_factory=FakeClient,
                                 token_provider=lambda: reads.append("read") or TOKEN,
                                 pool=pool)
        try:
            pane.origin.setText("https://zabbix-a.example.test/zabbix")
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(reads, ["read"])
            self.assertEqual(constructions, ["https://zabbix-a.example.test/zabbix"])
            self.assertEqual(pane.table.topLevelItemCount(), 1)

            pane.origin.setText("https://zabbix-b.example.test/zabbix")
            self.assertFalse(pane.consent.isChecked(), "editing the target must revoke prior consent")
            self.assertEqual(pane.table.topLevelItemCount(), 0, "old-target data must be cleared")
            self.assertIn("révoqué", pane.status.text().casefold())

            pane.refresh()  # No fresh consent: must remain offline.
            self.app.processEvents()
            self.assertEqual(reads, ["read"], "no token read without fresh consent")
            self.assertEqual(len(constructions), 1, "no request to the new origin without re-consent")
        finally:
            pane.close()
            pool.waitForDone(3000)

    def test_origin_edit_during_request_cancels_worker_and_discards_stale_result(self):
        entered = threading.Event()
        release = threading.Event()
        reads = []

        class BlockingClient:
            def __init__(self, origin, *, timeout, max_problems):
                self.origin = origin
            def problems(self, *, online, token, limit, cancelled):
                entered.set()
                release.wait(3)
                # Simulate a late response even though the worker was cancelled.
                return dashboard_snapshot("STALE_ALERT_FROM_OLD_ORIGIN")

        pool = QThreadPool()
        pane = ZabbixAlertsPanel([], client_factory=BlockingClient,
                                 token_provider=lambda: reads.append("read") or TOKEN,
                                 pool=pool)
        try:
            pane.origin.setText("https://zabbix-a.example.test")
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(entered.wait(2), "worker never reached the bounded fake transport")
            pane.origin.setText("https://zabbix-b.example.test")
            self.assertFalse(pane.consent.isChecked())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            release.set()
            self.assertTrue(pool.waitForDone(4000), "cancelled worker exceeded its bounded test deadline")
            self.app.processEvents()
            QTest.qWait(20)
            self.app.processEvents()
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertNotIn("STALE_ALERT_FROM_OLD_ORIGIN", pane.status.text())
            self.assertEqual(reads, ["read"], "the old in-flight read is not repeated at the new target")
        finally:
            release.set()
            pane.close()
            pool.waitForDone(3000)


if __name__ == "__main__":
    unittest.main()
