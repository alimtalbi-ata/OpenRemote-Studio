import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class WindowsV165Tests(unittest.TestCase):
    def test_one_click_entry(self):
        self.assertIn('bootstrap-and-build.ps1', (ROOT/'windows/BUILD-WINDOWS.cmd').read_text())
    def test_build_report_read_only(self):
        s=(ROOT/'windows/build-environment-report.ps1').read_text()
        self.assertIn('ConvertTo-Json',s)
        self.assertNotIn('Invoke-WebRequest',s)
        self.assertNotIn('Start-Process',s)
    def test_bootstrap_logs_report(self):
        self.assertIn("build-environment-report.ps1",(ROOT/'windows/bootstrap-and-build.ps1').read_text())
    def test_bootstrap_checks_powershell_failure(self):
        self.assertIn("if (-not $?) { throw 'Windows build script failed' }",(ROOT/'windows/bootstrap-and-build.ps1').read_text())
    def test_gui_smoke_checks_powershell_failure(self):
        self.assertIn("if (-not $?) { throw 'Packaged Windows GUI smoke failed' }",(ROOT/'windows/build-windows.ps1').read_text())
    def test_release_checks_powershell_failure(self):
        self.assertIn("if (-not $?) { throw 'Release verification failed' }",(ROOT/'windows/build-windows.ps1').read_text())
