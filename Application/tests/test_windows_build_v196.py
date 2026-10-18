import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BuildContract196(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf-8')
    def test_generated_dist_cleaned_before_pyinstaller(self):
        self.assertLess(self.script.index('Remove-Item -LiteralPath $generated'), self.script.index('& $python -m PyInstaller'))
    def test_clean_only_generated_directories(self):
        self.assertIn("$distDir = Join-Path $root 'dist'",self.script)
        self.assertIn("$workDir = Join-Path $root 'build'",self.script)
    def test_pe_header_checked_before_smoke(self):
        self.assertLess(self.script.index('ReadUInt32() -ne 0x00004550'),self.script.index("'smoke-windows.ps1'"))
    def test_binary_size_and_offset_checked(self):
        self.assertIn('Length -lt 512',self.script)
        self.assertIn('$peOffset -lt 64',self.script)
    def test_installer_has_onefile_and_onedir_modes(self):
        iss=(ROOT/'windows/OpenRemoteStudio.iss').read_text()
        self.assertIn('#ifdef SingleExeBuild',iss)
        self.assertIn('version.generated.iss',iss)
