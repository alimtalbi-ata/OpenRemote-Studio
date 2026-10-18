import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class WindowsInstallSmokeTests(unittest.TestCase):
    def test_install_smoke_exists(self):
        self.assertTrue((ROOT/'windows/install-smoke-windows.ps1').is_file())
    def test_isolated_profile(self):
        source=(ROOT/'windows/install-smoke-windows.ps1').read_text(encoding='utf-8')
        for token in ('$env:APPDATA = $roaming', '$env:LOCALAPPDATA = $local', '$env:APPDATA = $oldAppData', '$env:LOCALAPPDATA = $oldLocalAppData'):
            self.assertIn(token,source)
    def test_install_smoke_checks_all_phases(self):
        source=(ROOT/'windows/install-smoke-windows.ps1').read_text(encoding='utf-8')
        for token in ('/VERYSILENT', 'smoke-windows.ps1', 'unins000.exe', 'Executable still present after uninstall'):
            self.assertIn(token,source)
    def test_build_is_opt_in(self):
        source=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('[switch]$RunInstallSmoke',source)
        self.assertIn('if ($RunInstallSmoke -and $SkipInstaller)',source)
        self.assertIn('if ($RunInstallSmoke) {',source)
    def test_version_consistency(self):
        for name in ('build-windows.ps1','verify-release.ps1','OpenRemoteStudio.iss'):
            source=(ROOT/'windows'/name).read_text(encoding='utf-8')
            self.assertIn('version.generated.iss' if name.endswith('.iss') else '$releaseVersion',source)
            self.assertNotIn('15.8',source)
