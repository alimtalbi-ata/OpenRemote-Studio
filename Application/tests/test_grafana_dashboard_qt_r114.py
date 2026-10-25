"""R114 Qt regressions: offline default, consent revocation and safe deep links.
No Grafana instance, real token, or external network is used.
Author: Abdelhalim Talbi.
"""
import os
import threading
import unittest

try:
    from PySide6.QtCore import QThreadPool, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from grafana_dashboard_qt import GrafanaDashboardsPanel, _Fetch
except ImportError:
    QApplication = QThreadPool = QTest = GrafanaDashboardsPanel = _Fetch = Qt = None

ORIGIN = "https://grafana.example.test"
TOKEN = "R114_QT_FAKE_TOKEN_DO_NOT_DISPLAY"


def wait_until(app, predicate, ticks=300):
    for _ in range(ticks):
        app.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


def snapshot(uid="cpu-1", title="CPU Production", url="https://evil.example/steal"):
    return {"state": "ok", "read_only": True, "count": 1, "query": "",
            "dashboards": [{"uid": uid, "title": title, "folder": "Operations",
                            "tags": ["prod", "capacity"], "url": url}]}


@unittest.skipIf(QApplication is None, "PySide6 unavailable: Qt tests run in Windows native CI")
class GrafanaDashboardQtR114Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def make_panel(self, client_factory, token_reads, **kwargs):
        pool = QThreadPool()
        pane = GrafanaDashboardsPanel(
            client_factory=client_factory,
            token_provider=lambda: token_reads.append("read") or TOKEN,
            pool=pool,
            **kwargs,
        )
        return pane, pool

    def test_offline_default_never_constructs_client_or_reads_token(self):
        calls = []
        def forbidden(*args, **kwargs):
            calls.append("client")
            raise AssertionError("offline client construction")
        pane, pool = self.make_panel(forbidden, calls)
        try:
            self.assertFalse(pane.consent.isChecked())
            pane.refresh()
            self.assertEqual(calls, [])
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertIn("Hors ligne", pane.status.text())
        finally:
            pane.close()
            pool.waitForDone(3000)

    def test_success_uses_built_link_and_opens_only_after_operator_click(self):
        calls, token_reads, opened = [], [], []
        class FakeClient:
            def __init__(self, origin, *, timeout, max_dashboards):
                calls.append(("construct", origin, timeout, max_dashboards))
            def dashboards(self, *, online, token, query, cancelled):
                calls.append(("request", online, query))
                if token != TOKEN:
                    raise AssertionError("unexpected token")
                return snapshot()
        pool = QThreadPool()
        pane = GrafanaDashboardsPanel(
            client_factory=FakeClient,
            token_provider=lambda: token_reads.append("read") or TOKEN,
            pool=pool, url_opener=lambda url: opened.append(url) or True,
        )
        try:
            pane.origin.setText(ORIGIN)
            pane.query.setText("CPU")
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(len(calls), 2)
            self.assertEqual(token_reads, ["read"])
            self.assertEqual(pane.table.topLevelItemCount(), 1)
            item = pane.table.topLevelItem(0)
            self.assertEqual(item.text(0), "CPU Production")
            self.assertIn(ORIGIN + "/d/cpu-1/cpu-production", item.toolTip(0))
            self.assertNotIn(TOKEN, pane.status.text() + item.toolTip(0))
            self.assertEqual(opened, [], "loading a dashboard list must not launch a browser")
            pane.table.setCurrentItem(item)
            self.app.processEvents()
            self.assertTrue(pane.open_button.isEnabled())
            pane.open_selected()
            self.assertEqual(len(opened), 1)
            self.assertEqual(opened[0].toString(), ORIGIN + "/d/cpu-1/cpu-production")
            self.assertNotIn("evil.example", opened[0].toString())
            self.assertEqual(sum(1 for call in calls if call[0] == "request"), 1)
        finally:
            pane.close()
            pool.waitForDone(3000)

    def test_origin_edit_revokes_consent_clears_results_and_requires_new_token_read(self):
        calls, token_reads = [], []
        class FakeClient:
            def __init__(self, origin, *, timeout, max_dashboards):
                calls.append(("construct", origin))
            def dashboards(self, *, online, token, query, cancelled):
                calls.append(("request", online))
                return snapshot()
        pool = QThreadPool()
        pane = GrafanaDashboardsPanel(
            client_factory=FakeClient,
            token_provider=lambda: token_reads.append("read") or TOKEN,
            pool=pool,
        )
        try:
            pane.origin.setText(ORIGIN)
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(len(token_reads), 1)
            self.assertEqual(pane.table.topLevelItemCount(), 1)
            pane.origin.setText("https://grafana-next.example.test")
            self.assertFalse(pane.consent.isChecked())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertIn("révoqué", pane.status.text().casefold())
            pane.refresh()
            self.assertEqual(len(token_reads), 1)
            self.assertEqual(sum(1 for call in calls if call[0] == "request"), 1)
            self.assertIn("hors ligne", pane.status.text().casefold())
        finally:
            pane.close()
            pool.waitForDone(3000)

    def test_query_edit_also_revokes_consent(self):
        token_reads, calls = [], []
        class FakeClient:
            def __init__(self, origin, *, timeout, max_dashboards):
                pass
            def dashboards(self, **kwargs):
                calls.append("request")
                return snapshot()
        pool = QThreadPool()
        pane = GrafanaDashboardsPanel(
            client_factory=FakeClient,
            token_provider=lambda: token_reads.append("read") or TOKEN,
            pool=pool,
        )
        try:
            pane.origin.setText(ORIGIN)
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            pane.query.setText("new query")
            self.assertFalse(pane.consent.isChecked())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            pane.refresh()
            self.assertEqual(calls, ["request"])
            self.assertEqual(token_reads, ["read"])
        finally:
            pane.close()
            pool.waitForDone(3000)

    def test_invalid_origin_fails_before_token_provider(self):
        token_reads = []
        pane = GrafanaDashboardsPanel(token_provider=lambda: token_reads.append(True) or TOKEN)
        try:
            pane.origin.setText("http://not-https.example.test")
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane.refresh_button.isEnabled()))
            self.assertEqual(token_reads, [])
            self.assertIn("grafana_invalid_https_origin", pane.status.text())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
        finally:
            pane.close()

    def test_cancel_revokes_consent_and_prevents_overlap_until_worker_drains(self):
        entered, release = threading.Event(), threading.Event()
        calls, token_reads = [], []

        class BlockingClient:
            def __init__(self, origin, *, timeout, max_dashboards):
                calls.append(("construct", origin))
            def dashboards(self, *, online, token, query, cancelled):
                calls.append(("request", online))
                entered.set()
                release.wait(3)
                return snapshot(title="CANCELLED_RESULT_MUST_NOT_APPEAR")

        pool = QThreadPool()
        pane = GrafanaDashboardsPanel(
            client_factory=BlockingClient,
            token_provider=lambda: token_reads.append("read") or TOKEN,
            pool=pool,
        )
        try:
            pane.origin.setText(ORIGIN)
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(entered.wait(2), "the explicit request should start")
            pane.cancel_request()
            self.assertFalse(pane.consent.isChecked(), "cancel must revoke online consent")
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertIsNotNone(pane._pending, "keep the worker fenced until it drains")
            self.assertFalse(pane.refresh_button.isEnabled())
            pane.refresh()
            self.assertEqual(sum(1 for item in calls if item[0] == "request"), 1,
                             "cancellation must not create an overlapping network request")
            self.assertEqual(token_reads, ["read"])
            self.assertIn("consentement révoqué", pane.status.text().casefold())

            release.set()
            self.assertTrue(pool.waitForDone(4000))
            self.app.processEvents()
            self.assertIsNone(pane._pending)
            self.assertFalse(pane.consent.isChecked())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertTrue(pane.refresh_button.isEnabled())
            self.assertNotIn("CANCELLED_RESULT_MUST_NOT_APPEAR", pane.status.text())

            # A deliberate re-approval after the prior worker has drained is allowed.
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(sum(1 for item in calls if item[0] == "request"), 2)
            self.assertEqual(token_reads, ["read", "read"])
        finally:
            release.set()
            pane.close()
            pool.waitForDone(3000)

    def test_stale_response_after_consent_revocation_is_never_rendered(self):
        entered, release = threading.Event(), threading.Event()
        class BlockingClient:
            def __init__(self, origin, *, timeout, max_dashboards):
                pass
            def dashboards(self, *, online, token, query, cancelled):
                entered.set()
                release.wait(3)
                return snapshot(title="STALE_DASHBOARD_MUST_NOT_APPEAR")
        pool = QThreadPool()
        pane = GrafanaDashboardsPanel(
            client_factory=BlockingClient,
            token_provider=lambda: TOKEN,
            pool=pool,
        )
        try:
            pane.origin.setText(ORIGIN)
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(entered.wait(2))
            pane.consent.setChecked(False)
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            release.set()
            self.assertTrue(pool.waitForDone(4000))
            self.app.processEvents()
            QTest.qWait(50)
            self.app.processEvents()
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertNotIn("STALE_DASHBOARD_MUST_NOT_APPEAR", pane.status.text())
        finally:
            release.set()
            pane.close()
            pool.waitForDone(3000)

    def test_injected_bad_uid_is_rejected_without_crashing_or_opening_external_url(self):
        opened = []
        class FakeClient:
            def __init__(self, origin, *, timeout, max_dashboards):
                pass
            def dashboards(self, **kwargs):
                return snapshot(uid=["not", "a", "uid"])
        pool = QThreadPool()
        pane = GrafanaDashboardsPanel(client_factory=FakeClient, pool=pool,
                                      url_opener=lambda url: opened.append(url))
        try:
            pane.origin.setText(ORIGIN)
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(pane.table.topLevelItemCount(), 0)
            self.assertIn("grafana_invalid_dashboard", pane.status.text())
            self.assertEqual(opened, [])
        finally:
            pane.close()
            pool.waitForDone(3000)

    def test_transport_exception_is_redacted(self):
        class FakeClient:
            def __init__(self, origin, *, timeout, max_dashboards):
                pass
            def dashboards(self, **kwargs):
                raise RuntimeError("transport leaked " + TOKEN)
        pool = QThreadPool()
        pane = GrafanaDashboardsPanel(client_factory=FakeClient, pool=pool,
                                      token_provider=lambda: TOKEN)
        try:
            pane.origin.setText(ORIGIN)
            pane.consent.setChecked(True)
            pane.refresh()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertIn("grafana_unavailable", pane.status.text())
            self.assertNotIn(TOKEN, pane.status.text())
            self.assertEqual(pane.table.topLevelItemCount(), 0)
        finally:
            pane.close()
            pool.waitForDone(3000)

    def test_pre_cancelled_worker_never_constructs_client_or_reads_token(self):
        calls = []
        worker = _Fetch(3, ORIGIN, "", lambda: calls.append("token"),
                        lambda *a, **kw: calls.append("client"))
        emitted = []
        worker.signals.finished.connect(lambda generation, result: emitted.append((generation, result)))
        worker.cancel()
        worker.run()
        self.assertEqual(calls, [])
        self.assertEqual(emitted[0][0], 3)
        self.assertEqual(emitted[0][1]["state"], "cancelled")


if __name__ == "__main__":
    unittest.main()
