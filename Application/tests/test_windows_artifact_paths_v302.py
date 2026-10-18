"""Regression checks for V30.2 release path interpolation."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / "Application/windows/build-windows.ps1").read_text(encoding="utf-8")

class ArtifactPathTests(unittest.TestCase):
    def test_portable_path_expands_release_version(self):
        self.assertIn('"Portable\\OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip"', SCRIPT)
        self.assertNotIn("'Portable\\OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip'", SCRIPT)

    def test_installer_path_expands_release_version(self):
        self.assertIn('"Installer\\OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe"', SCRIPT)
        self.assertNotIn("'Installer\\OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe'", SCRIPT)

    def test_binary_root_and_manifest_present(self):
        self.assertIn("'Binary'", SCRIPT)
        self.assertIn("'SHA256SUMS.txt'", SCRIPT)
        self.assertIn("verify-release.ps1", SCRIPT)
