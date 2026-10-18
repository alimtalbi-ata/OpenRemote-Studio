import json
import tempfile
import unittest
from pathlib import Path
from offline_qualification import run_offline, write_offline_report

ROOT = Path(__file__).resolve().parents[1]

class OfflineQualificationTests(unittest.TestCase):
    def test_offline_source_passes(self):
        r=run_offline(ROOT)
        self.assertEqual(r["offline_checks"][0]["status"], "passed")
    def test_entrypoint_parses(self):
        self.assertEqual(run_offline(ROOT)["offline_checks"][1]["status"], "passed")
    def test_tests_not_run_by_default(self):
        self.assertEqual(run_offline(ROOT)["offline_checks"][2]["status"], "not_executed")
    def test_manual_scenarios_untouched(self):
        self.assertTrue(all(x["status"]=="not_executed" for x in run_offline(ROOT)["scenarios"]))
    def test_no_false_live_claims(self):
        r=run_offline(ROOT)
        self.assertEqual((r["live_tests_executed"],r["gui_tests_executed"]),(0,0))
    def test_missing_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=run_offline(tmp)
            self.assertEqual(r["offline_checks"][1]["detail"],"entrypoint_missing")
    def test_invalid_timeout(self):
        for value in (0,601,True,1.5):
            with self.subTest(value=value),self.assertRaises(ValueError):run_offline(ROOT,timeout=value)
    def test_report_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"report.json"
            write_offline_report(ROOT,p)
            self.assertEqual(json.loads(p.read_text())["offline_checks_passed"],2)
            with self.assertRaises(FileExistsError):write_offline_report(ROOT,p)
    def test_no_sensitive_details(self):
        r=run_offline(ROOT)
        self.assertNotIn("private_key",json.dumps(r))
