"""R116 headless Qt interaction tests; all check-mode execution is injected/fake."""
import os
import tempfile
import threading
import unittest
from pathlib import Path

try:
    from PySide6.QtCore import QThreadPool
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from ansible_preflight_qt import AnsiblePreflightPanel
except ImportError:
    QApplication = QThreadPool = QTest = AnsiblePreflightPanel = None

PLAYBOOK = """- name: Read-only check
  hosts: servers
  gather_facts: false
  tasks:
    - name: Validate transport
      ansible.builtin.ping: {}
"""
INVENTORY = "[servers]\nnode1.example.test\n"


def wait_until(app, predicate, ticks=250):
    for _ in range(ticks):
        app.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    return False


@unittest.skipIf(QApplication is None, "PySide6 unavailable: Qt tests run in Windows CI")
class AnsiblePreflightQtR116Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # The selected private key fixture must satisfy the same verified DACL
        # contract used by the real Ansible runner on Windows.
        from winrm_readonly import private_temporary_directory
        self._temp_context = private_temporary_directory()
        temporary, self._fixture_user_sid = self._temp_context.__enter__()
        self.root = Path(temporary)
        self.playbook = self.root / "safe.yml"
        self.inventory = self.root / "hosts.ini"
        self.hosts = self.root / "known_hosts"
        self.key = self.root / "id_key"
        self.playbook.write_text(PLAYBOOK, encoding="utf-8")
        self.inventory.write_text(INVENTORY, encoding="utf-8")
        self.hosts.write_text("node1.example.test ssh-ed25519 QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=\n", encoding="utf-8")
        self.key.write_text("synthetic key fixture", encoding="utf-8")
        if os.name != "nt":
            os.chmod(self.key, 0o600)
        self.pool = QThreadPool()

    def tearDown(self):
        self.pool.waitForDone(3000)
        self._temp_context.__exit__(None, None, None)

    def make_panel(self, *, runner=None, analyzer=None, lookup=None):
        pane = AnsiblePreflightPanel(
            analyzer=analyzer,
            runner=runner,
            executable_lookup=lookup or (lambda _name: None),
            pool=self.pool,
        )
        pane.playbook_path.setText(str(self.playbook))
        pane.inventory_path.setText(str(self.inventory))
        pane.known_hosts_path.setText(str(self.hosts))
        pane.private_key_path.setText(str(self.key))
        return pane

    def test_offline_default_and_analyze_never_start_check_runner(self):
        calls = []
        def runner(**kwargs):
            calls.append(kwargs)
            return {"state": "check_succeeded"}
        pane = self.make_panel(runner=runner)
        try:
            self.assertFalse(pane.consent.isChecked())
            self.assertFalse(pane.run_button.isEnabled())
            pane.analyze_button.click()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(calls, [])
            self.assertIn("Prévalidation réussie", pane.status.text())
            self.assertEqual(pane.summary.topLevelItemCount(), 1)
            self.assertFalse(pane.run_button.isEnabled(), "a missing CLI must disable remote execution")
        finally:
            pane.close()

    def test_explicit_consent_runs_only_injected_check_mode_and_reapproves_afterward(self):
        calls = []
        def runner(**kwargs):
            calls.append(kwargs)
            return {"state": "check_succeeded", "read_only": True,
                    "output_retained": False, "host_count": 1, "task_count": 1}
        pane = self.make_panel(runner=runner, lookup=lambda _name: "/fake/ansible-playbook")
        try:
            pane.analyze_button.click()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertTrue(pane._analysis)
            self.assertFalse(pane.consent.isChecked())
            self.assertFalse(pane.run_button.isEnabled())
            pane.consent.setChecked(True)
            self.assertTrue(pane.run_button.isEnabled())
            approved_connection_fingerprints = dict(pane._connection_fingerprints)
            pane.run_button.click()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0]["consent"])
            self.assertEqual(calls[0]["expected_playbook_sha256"], pane._analysis["playbook_sha256"])
            self.assertEqual(calls[0]["expected_inventory_sha256"], pane._analysis["inventory_sha256"])
            self.assertEqual(calls[0]["expected_known_hosts_sha256"], approved_connection_fingerprints["known_hosts_sha256"])
            self.assertEqual(calls[0]["expected_private_key_sha256"], approved_connection_fingerprints["private_key_sha256"])
            self.assertNotIn("synthetic key fixture", pane.status.text())
            self.assertFalse(pane.consent.isChecked(), "consent is one-shot")
            self.assertNotIn("stdout", pane.status.text().lower())
        finally:
            pane.close()

    def test_editing_any_input_revokes_consent_and_clears_preview(self):
        pane = self.make_panel(lookup=lambda _name: "/fake/ansible-playbook")
        try:
            pane.analyze_button.click()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(pane.summary.topLevelItemCount(), 1)
            pane.consent.setChecked(True)
            self.assertTrue(pane.run_button.isEnabled())
            pane.inventory_path.setText(str(self.root / "other.ini"))
            self.assertFalse(pane.consent.isChecked())
            self.assertIsNone(pane._analysis)
            self.assertEqual(pane.summary.topLevelItemCount(), 0)
            self.assertFalse(pane.run_button.isEnabled())
            self.assertIn("révoqué", pane.status.text())
        finally:
            pane.close()

    def test_invalid_known_hosts_refuses_consent_before_runner_invocation(self):
        self.hosts.write_text("not a valid host key\n", encoding="utf-8")
        calls = []
        def runner(**kwargs):
            calls.append(kwargs)
            return {"state": "check_succeeded"}
        pane = self.make_panel(runner=runner, lookup=lambda _name: "/fake/ansible-playbook")
        try:
            pane.analyze_button.click()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            pane.consent.setChecked(True)
            self.assertFalse(pane.consent.isChecked())
            self.assertFalse(pane.run_button.isEnabled())
            self.assertEqual(calls, [])
            self.assertIn("Consentement refusé", pane.status.text())
            self.assertNotIn("synthetic key fixture", pane.status.text())
        finally:
            pane.close()

    def test_stale_async_result_is_not_rendered_after_path_edit(self):
        entered = threading.Event()
        release = threading.Event()
        from ansible_preflight import analyze_playbook
        def blocking_analyzer(**kwargs):
            entered.set()
            release.wait(3)
            return analyze_playbook(**kwargs)
        pane = self.make_panel(analyzer=blocking_analyzer)
        try:
            pane.analyze_button.click()
            self.assertTrue(entered.wait(2))
            pane.playbook_path.setText(str(self.root / "changed.yml"))
            release.set()
            self.assertTrue(wait_until(self.app, lambda: pane._pending is None))
            self.assertEqual(pane.summary.topLevelItemCount(), 0)
            self.assertIsNone(pane._analysis)
            self.assertIn("Annulation demandée", pane.status.text())
        finally:
            release.set()
            pane.close()


if __name__ == "__main__":
    unittest.main()
