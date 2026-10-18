import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / "02-Compilation" / "TEST-CONCURRENCE-WINDOWS.ps1").read_text(encoding="utf-8")

class CrashRecoveryContract(unittest.TestCase):
    def test_forced_process_termination(self):
        self.assertIn("Stop-Process -Id $crashProbe.Id -Force", SCRIPT)
    def test_recovery_probed_after_exit(self):
        self.assertLess(SCRIPT.index("$crashProbe.WaitForExit(10000)"), SCRIPT.index("$recovered = Start-Process"))
    def test_failed_recovery_is_error(self):
        self.assertIn("Lock not released after forced process termination", SCRIPT)
    def test_cleanup_finally(self):
        self.assertIn("if (-not $crashProbe.HasExited)", SCRIPT)
