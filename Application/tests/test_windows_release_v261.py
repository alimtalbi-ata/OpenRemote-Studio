import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReleaseVersionTests(unittest.TestCase):
 def test_build_outputs_current_version(self):
  s=(ROOT/'windows/build-windows.ps1').read_text()
  self.assertIn('OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip',s)
  self.assertIn('OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe',s)
  self.assertNotIn('V24.2-Windows-',s)
 def test_verifier_checks_current_artifacts(self):
  s=(ROOT/'windows/verify-release.ps1').read_text()
  self.assertIn('OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip',s)
  self.assertIn('OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe',s)
 def test_inno_version_and_output(self):
  s=(ROOT/'windows/OpenRemoteStudio.iss').read_text()
  self.assertIn('#include "version.generated.iss"',s)
  self.assertIn('OutputBaseFilename=OpenRemoteStudio-V{#MyAppVersion}-Windows-Setup',s)
 def test_root_version(self):
  self.assertEqual((ROOT.parent/'VERSION.txt').read_text().strip(),(ROOT.parent/'VERSION.txt').read_text().strip())
