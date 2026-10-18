import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class WindowsRelease157(unittest.TestCase):
 def test_preflight_platform(self):
  s=(ROOT/'windows/preflight-windows.ps1').read_text()
  self.assertIn("Windows_NT",s)
  self.assertIn("Is64BitOperatingSystem",s)
  self.assertIn("3,11",s)
 def test_preflight_installer_optional(self):
  s=(ROOT/'windows/preflight-windows.ps1').read_text()
  self.assertIn('SkipInstaller',s)
  self.assertIn('ISCC.exe',s)
 def test_build_calls_preflight(self):
  s=(ROOT/'windows/build-windows.ps1').read_text()
  self.assertIn('preflight-windows.ps1',s)
  self.assertIn('verify-release.ps1',s)
 def test_release_zip_exe(self):
  s=(ROOT/'windows/verify-release.ps1').read_text()
  self.assertIn('OpenRemoteStudio.exe',s)
  self.assertIn('ZipFile',s)
 def test_release_version(self):
  self.assertIn('version.generated.iss',(ROOT/'windows/OpenRemoteStudio.iss').read_text())
  self.assertIn('releaseVersion',(ROOT/'windows/build-windows.ps1').read_text())
