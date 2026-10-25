"""R109 Qt contract: online consent, redaction, local-only filters and stale-result fencing.

No Zabbix server, API token, or external network is used. Author: Abdelhalim Talbi.
"""
import os
import threading
import unittest

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from zabbix_alerts_qt import ZabbixAlertsPanel, _Fetch
except ImportError:
    QApplication = None


TOKEN = "R109_QT_FAKE_TOKEN_DO_NOT_DISPLAY"


def wait_until(app, predicate, ticks=300):
    for _ in range(ticks):
        app.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


def snapshot(*rows):
    return {"state": "ok", "read_only": True, "problems": list(rows),
            "limit": 50, "may_be_truncated": False}


def row(name="Disk space low", host="srv01", severity=4, acknowledged=False):
    return {"event_id": "101", "name": name, "severity": severity,
            "severity_label": ("Non classée", "Information", "Avertissement", "Moyenne", "Haute", "Désastre")[severity],
            "last_change": 1790000000, "acknowledged": acknowledged,
            "hosts": [{"host": host, "name": host.upper()}],
            "trigger_description": "Disk threshold"}


@unittest.skipIf(QApplication is None, "PySide6 unavailable: Qt tests run in Windows native CI")
class ZabbixAlertsQtR109Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_offline_default_never_constructs_client_or_reads_token(self):
        calls = []
        def forbidden(*args, **kwargs):
            calls.append("client")
            raise AssertionError("offline client construction")
        pane = ZabbixAlertsPanel([], client_factory=forbidden,
                                 token_provider=lambda: calls.append("token"))
        try:
            self.assertFalse(pane.consent.isChecked())
            pane.refresh()
            self.assertEqual(calls, [])
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertIn("Hors ligne", pane.status.text())
        finally:
            pane.close()

    def test_pre_cancelled_worker_never_constructs_client_or_reads_token(self):
        calls = []
        worker = _Fetch(4, "https://zabbix.example.test", [], 10,
                        lambda *a, **k: calls.append("client"),
                        lambda: calls.append("token"))
        emitted = []
        worker.signals.finished.connect(lambda generation, result: emitted.append((generation, result)))
        worker.cancel()
        worker.run()
        self.assertEqual(calls, [])
        self.assertEqual(emitted[0][0], 4)
        self.assertEqual(emitted[0][1]["state"], "cancelled")

    def test_invalid_https_origin_fails_before_token_provider(self):
        reads = []
        pane = ZabbixAlertsPanel([], token_provider=lambda: reads.append(True) or TOKEN)
        try:
            pane.origin.setText("http://untrusted.example.test")
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))
            self.assertEqual(reads, [])
            self.assertIn("zabbix_invalid_https_origin", pane.status.text())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
        finally:
            pane.close()

    def test_success_matches_only_host_protocol_name_and_local_filter_never_refetches(self):
        client_calls = []
        token_reads = []
        class FakeClient:
            def __init__(self, origin, *, timeout, max_problems):
                self.origin = origin
                self.max_problems = max_problems
            def problems(self, *, online, token, limit, cancelled):
                client_calls.append((self.origin, online, limit))
                token_reads.append(token)
                self.assert_true = online is True
                if token != TOKEN:
                    raise AssertionError("wrong token")
                second = dict(row(name="CPU busy", host="node-b", severity=3), event_id="102")
                return snapshot(row(), second)
        class Profile(dict):
            def __getitem__(self, key):
                if key in ("password", "user", "token", "private_key"):
                    raise AssertionError("secret field accessed")
                return super().__getitem__(key)
        connections = [
            Profile(name="Production SSH", protocol="SSH", host="srv01.", password="never-read"),
            Profile(name="Other RDP", protocol="RDP", host="unused", user="never-read"),
        ]
        pane = ZabbixAlertsPanel(connections, client_factory=FakeClient,
                                 token_provider=lambda: TOKEN)
        try:
            pane.origin.setText("https://zabbix.example.test/zabbix")
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))
            self.assertEqual(client_calls, [("https://zabbix.example.test/zabbix", True, 50)])
            self.assertEqual(token_reads, [TOKEN])
            self.assertEqual(pane.table.topLevelItemCount(), 2)
            first = pane.table.topLevelItem(0)
            self.assertIn("Production SSH [SSH]", first.text(5))
            self.assertNotIn(TOKEN, pane.status.text() + first.text(4) + first.text(5))
            pane.search_filter.setText("CPU")
            self.app.processEvents()
            self.assertEqual(pane.table.topLevelItemCount(), 1)
            self.assertEqual(pane.table.topLevelItem(0).text(4), "CPU busy")
            pane.severity_filter.setCurrentIndex(pane.severity_filter.findData(3))
            self.assertEqual(pane.table.topLevelItemCount(), 1)
            self.assertEqual(len(client_calls), 1)
        finally:
            pane.close()

    def test_consent_revocation_discards_stale_inflight_result(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        class FakeClient:
            def __init__(self, origin, *, timeout, max_problems):
                pass
            def problems(self, *, online, token, limit, cancelled):
                calls.append("request")
                entered.set()
                release.wait(3)
                return snapshot(row(name="STALE_PRIVATE_ALERT"))
        pane = ZabbixAlertsPanel([], client_factory=FakeClient,
                                 token_provider=lambda: TOKEN)
        try:
            pane.origin.setText("https://zabbix.example.test")
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(entered.wait(2))
            pane.consent.setChecked(False)
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            release.set()
            self.assertTrue(wait_until(self.app, lambda: len(calls) == 1 and pane._pending is None))
            QTest.qWait(50)
            self.app.processEvents()
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertNotIn("STALE_PRIVATE_ALERT", pane.status.text())
        finally:
            release.set()
            pane.close()

    def test_transport_exception_with_token_is_redacted(self):
        class FakeClient:
            def __init__(self, origin, *, timeout, max_problems):
                pass
            def problems(self, *, online, token, limit, cancelled):
                raise RuntimeError("transport leaked " + token)
        pane = ZabbixAlertsPanel([], client_factory=FakeClient,
                                 token_provider=lambda: TOKEN)
        try:
            pane.origin.setText("https://zabbix.example.test")
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))
            self.assertIn("zabbix_unavailable", pane.status.text())
            self.assertNotIn(TOKEN, pane.status.text())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
        finally:
            pane.close()


if __name__ == "__main__":
    unittest.main()
