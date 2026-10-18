import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class ReleaseIntegrityV180(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verify=(ROOT/'windows/verify-release.ps1').read_text(encoding='utf8')
        cls.build=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf8')
    def test_manifest_is_mandatory(self): self.assertIn('SHA256 manifest missing',self.verify)
    def test_actual_hash_verified(self): self.assertIn('Get-FileHash -LiteralPath $path -Algorithm SHA256',self.verify)
    def test_hash_mismatch_fails_closed(self): self.assertIn('SHA256 mismatch',self.verify)
    def test_duplicate_entry_rejected(self): self.assertIn('Duplicate SHA256 manifest entry',self.verify)
    def test_missing_entry_rejected(self): self.assertIn('Missing SHA256 entry',self.verify)
    def test_stale_setup_removed(self): self.assertIn('Never accept a stale setup binary',self.build)
    def test_current_version(self): self.assertIn('$releaseVersion',self.verify)
