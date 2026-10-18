import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class BinaryBuildContractTests(unittest.TestCase):
    def test_installer_has_pe_validation(self):
        code = (ROOT / 'Application/windows/build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('Installer lacks MZ signature', code)
        self.assertIn('Installer lacks PE signature', code)
        self.assertIn('Installer PE offset invalid', code)
    def test_binary_directories_are_explicit(self):
        self.assertTrue((ROOT / 'Binary/Installer').is_dir())
        self.assertTrue((ROOT / 'Binary/Portable').is_dir())
    def test_binary_folder_has_no_fake_executables(self):
        self.assertFalse(list((ROOT / 'Binary').rglob('*.exe')))
