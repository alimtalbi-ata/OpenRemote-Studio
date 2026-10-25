"""R115 security and QA contract for packaged GUI startup diagnostics.

The suite does not start the packaged application or contact any remote host.
Author: Abdelhalim Talbi.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "Application"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from startup_diagnostics import record_startup


class PackagedSmokeDiagnosticsR115Tests(unittest.TestCase):
    def test_startup_journal_keeps_error_type_but_never_exception_message(self):
        secret_canary = "R115_DO_NOT_WRITE_THIS_FAKE_SECRET"
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "startup.jsonl"
            record_startup(
                "main_window",
                "failed",
                RuntimeError("synthetic exception carried " + secret_canary),
                path=target,
            )
            line = target.read_text(encoding="utf-8").strip()
            row = json.loads(line)
        self.assertEqual(row["stage"], "main_window")
        self.assertEqual(row["outcome"], "failed")
        self.assertEqual(row["error_type"], "RuntimeError")
        self.assertNotIn(secret_canary, line)
        self.assertEqual(set(row), {"schema", "utc", "stage", "outcome", "error_type"})

    def test_gui_smoke_stays_bounded_and_exports_only_redacted_evidence_on_failure(self):
        source = (ROOT / "Application/windows/smoke-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("[ValidateRange(5,120)][int]$TimeoutSeconds = 60", source)
        self.assertIn("startup.jsonl", source)
        self.assertIn("smoke-result.json", source)
        self.assertIn("failure_code = $failureCode", source)
        self.assertIn("redacted_startup_journal_copied = $copied", source)
        self.assertIn("Copy-Item -LiteralPath $diagnosticSource", source)
        self.assertIn("Sanitized startup evidence", source)
        self.assertNotIn("$_.Exception.Message", source)
        self.assertNotIn("$_.ScriptStackTrace", source)

    def test_onedir_and_portable_gui_smokes_use_same_sixty_second_budget(self):
        source = (ROOT / "Application/windows/build-windows.ps1").read_text(encoding="utf-8")
        gui_calls = [
            line.strip() for line in source.splitlines()
            if "smoke-windows.ps1" in line and "-Exe" in line
        ]
        self.assertEqual(len(gui_calls), 2, "expected onedir and extracted portable GUI smoke")
        self.assertTrue(all("-TimeoutSeconds 60" in line for line in gui_calls))
        runtime_calls = [line for line in source.splitlines() if "winrm-runtime-smoke.ps1" in line]
        self.assertEqual(len(runtime_calls), 2)
        self.assertTrue(all("-TimeoutSeconds 30" in line for line in runtime_calls),
                        "WinRM dependency smoke keeps its separate bound")

    def test_workflow_keeps_hard_deadline_and_uploads_sanitized_diagnostics(self):
        source = (ROOT / ".github/workflows/windows-native.yml").read_text(encoding="utf-8")
        self.assertIn("-Exe $exe -TimeoutSeconds 60", source)
        self.assertIn("Binary/Qualification/**", source)
        self.assertIn("openremote-windows-build-logs", source)

    def test_release_dossier_includes_r115_limitations(self):
        source = (ROOT / "02-Compilation/generate_release_dossier.py").read_text(encoding="utf-8")
        self.assertIn("V31.8-R115-GRAFANA-ORIGIN-HARDENING.md", source)
        self.assertIn("The increased limit is not itself proof", source)


if __name__ == "__main__":
    unittest.main()
