import pathlib
import re
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
class WindowsReleaseCleanupTests(unittest.TestCase):
    def test_cleanup_targets_current_version(self):
        script = (ROOT / "windows/build-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("^OpenRemoteStudio-V[0-9]+\\.[0-9]+-Windows-", script)
        self.assertNotIn("^OpenRemoteStudio-V18\\.3-Windows-", script)
    def test_setup_output_matches_release(self):
        iss = (ROOT / "windows/OpenRemoteStudio.iss").read_text(encoding="utf-8")
        build = (ROOT / "windows/build-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("OutputBaseFilename=OpenRemoteStudio-V{#MyAppVersion}-Windows-Setup", iss)
        self.assertIn("OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe", build)
    def test_cleanup_before_build(self):
        script = (ROOT / "windows/build-windows.ps1").read_text(encoding="utf-8")
        self.assertLess(script.index("Remove-Item -Force"), script.index("-m PyInstaller"))
