import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "windows/bootstrap-and-build.ps1").read_text(encoding="utf-8")

class BuildLockTests(unittest.TestCase):
    def test_exclusive_lock(self):
        self.assertIn("[IO.FileShare]::None", SCRIPT)
        self.assertIn("[IO.FileMode]::OpenOrCreate", SCRIPT)
        self.assertIn(".windows-build.lock", SCRIPT)
    def test_release_even_on_failure(self):
        self.assertIn("$buildLock.Dispose()", SCRIPT)
        self.assertIn("Stop-Transcript", SCRIPT)
    def test_unique_log_for_each_attempt(self):
        self.assertIn("Get-Date -Format 'yyyyMMdd-HHmmss-fff'", SCRIPT)
        self.assertIn("[guid]::NewGuid()", SCRIPT)
        self.assertNotIn("Start-Transcript -Path $log -Force", SCRIPT)
