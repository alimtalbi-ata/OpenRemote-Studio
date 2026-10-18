import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
class AtomicRelease(unittest.TestCase):
 def test_staging_is_unique(self):
  s=(ROOT/'Application/windows/build-windows.ps1').read_text()
  self.assertIn('[guid]::NewGuid()',s)
  self.assertIn('Move-Item -LiteralPath $release -Destination $published',s)
 def test_failed_build_does_not_delete_prior_versions(self):
  s=(ROOT/'Application/windows/build-windows.ps1').read_text()
  self.assertNotIn('Get-ChildItem -LiteralPath $release -File -Recurse -ErrorAction SilentlyContinue',s)
  self.assertIn('already published',s)
 def test_verify_paths_expand_version(self):
  s=(ROOT/'Application/windows/verify-release.ps1').read_text()
  self.assertIn('"Portable\\OpenRemoteStudio-V${releaseVersion}',s)
  self.assertIn('"Installer\\OpenRemoteStudio-V${releaseVersion}',s)
