import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class InstallSmokeV197(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / 'windows/install-smoke-windows.ps1').read_text()
        cls.builder = (ROOT / 'windows/build-windows.ps1').read_text()
    def test_default_setup_matches_release(self):
        self.assertIn('OpenRemoteStudio-V', self.script)
        self.assertIn('$releaseVersion', self.script)
        self.assertNotIn('OpenRemoteStudio-V16.0-Windows-Setup.exe', self.script)
    def test_install_and_uninstall_are_bounded(self):
        self.assertIn('WaitForExit($TimeoutSeconds * 1000)', self.script)
        self.assertIn('Invoke-BoundedInstaller -FilePath $SetupExe', self.script)
        self.assertIn('Invoke-BoundedInstaller -FilePath $uninstaller', self.script)
    def test_process_killed_on_timeout(self):
        self.assertIn('$proc.Kill()', self.script)
        self.assertIn('$proc.Dispose()', self.script)
    def test_isolated_install_and_profile(self):
        self.assertIn("[guid]::NewGuid()", self.script)
        self.assertIn('$env:APPDATA = $roaming', self.script)
        self.assertIn('$env:LOCALAPPDATA = $local', self.script)
    def test_build_propagates_timeout(self):
        self.assertIn('InstallSmokeTimeoutSeconds = 180', self.builder)
        self.assertIn('-TimeoutSeconds $InstallSmokeTimeoutSeconds', self.builder)
