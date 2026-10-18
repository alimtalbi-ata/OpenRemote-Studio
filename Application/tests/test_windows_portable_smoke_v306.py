"""Contracts for the extracted portable smoke in the Windows build pipeline."""
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'windows' / 'build-windows.ps1'

class PortableSmokeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding='utf-8-sig')

    def test_extract_archive_before_release_publication(self):
        s=self.source
        self.assertLess(s.index('Expand-Archive -LiteralPath $portable'),s.index('Move-Item -LiteralPath $release -Destination $published'))

    def test_smoke_extracted_executable(self):
        s=self.source
        self.assertIn("$portableExecutables[0].FullName -TimeoutSeconds 30",s)
        self.assertIn("if ($portableExecutables.Count -ne 1)",s)

    def test_staging_cleanup_on_failure(self):
        s=self.source
        self.assertIn('finally {\n  if (Test-Path -LiteralPath $portableSmokeDir)',s)

    def test_published_version_rejected_before_build(self):
        s=self.source
        self.assertLess(s.index('already published: $published'),s.index('& $python -m PyInstaller'))
