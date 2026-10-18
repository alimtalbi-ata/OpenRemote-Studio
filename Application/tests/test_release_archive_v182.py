import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ReleaseArchiveV182Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.script=(ROOT/'windows/verify-release.ps1').read_text(encoding='utf-8')
    def test_traversal_rejected(self): self.assertIn('Unsafe portable ZIP path',self.script)
    def test_duplicate_rejected(self): self.assertIn('Duplicate portable ZIP entry',self.script)
    def test_payload_read(self): self.assertIn('$stream.Read($buffer',self.script)
    def test_stream_disposed(self): self.assertIn('$stream.Dispose()',self.script)
    def test_unexpected_artifact_rejected(self): self.assertIn('Unexpected release artifact',self.script)
    def test_manifest_hash_validation_retained(self): self.assertIn('SHA256 mismatch:',self.script)
