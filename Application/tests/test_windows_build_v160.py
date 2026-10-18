"""Static checks for the Windows build safety contract (platform-independent)."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class WindowsBuildV160Tests(unittest.TestCase):
    def test_deadline(self):
        script=(ROOT/'windows/smoke-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('WaitForExit($TimeoutSeconds * 1000)',script)
        self.assertIn('$process.Kill()',script)
    def test_profile_isolation(self):
        script=(ROOT/'windows/smoke-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('$env:APPDATA = Join-Path $smokeRoot',script)
        self.assertIn('$env:APPDATA = $oldAppData',script)
    def test_build_uses_bounded_smoke(self):
        script=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn("'smoke-windows.ps1'",script)
        self.assertIn('-TimeoutSeconds 30',script)
        self.assertNotIn('& $exe --smoke-gui',script)
    def test_version(self):
        script=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('$releaseVersion',script)
