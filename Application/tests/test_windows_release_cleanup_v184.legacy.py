import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ReleaseCleanupV184Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / "windows" / "build-windows.ps1").read_text(encoding="utf-8")

    def test_all_versioned_installers_removed(self):
        self.assertIn("^OpenRemoteStudio-V[0-9]+\\.[0-9]+-Windows-", self.script)

    def test_portable_and_setup_in_cleanup(self):
        self.assertIn("Portable\\.zip|Setup\\.exe", self.script)

    def test_cleanup_precedes_pyinstaller(self):
        self.assertLess(self.script.index("Get-ChildItem -LiteralPath $release"), self.script.index("-m PyInstaller"))

    def test_current_setup_is_versioned(self):
        self.assertIn("OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe", self.script)
