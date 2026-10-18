"""Static regression checks for the closed release manifest (Windows script)."""
import unittest
from pathlib import Path
S=(Path(__file__).resolve().parents[1]/'windows/verify-release.ps1').read_text(encoding='utf-8')
class ClosedReleaseManifestTests(unittest.TestCase):
    def test_unexpected_manifest_entry_rejected(self):
        self.assertIn('Unexpected SHA256 manifest entry:', S)
    def test_every_manifest_entry_is_hashed(self):
        self.assertIn('foreach ($name in @($expected.Keys))', S)
        self.assertIn('Get-FileHash -LiteralPath $path -Algorithm SHA256', S)
    def test_manifest_file_must_exist(self):
        self.assertIn('Manifest artifact missing:', S)
    def test_zero_byte_artifact_rejected(self):
        self.assertIn('Empty release artifact:', S)
    def test_required_artifact_has_manifest_entry(self):
        self.assertIn('Missing SHA256 entry:', S)
if __name__=='__main__': unittest.main()
