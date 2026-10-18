import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class NativeQualificationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=(ROOT/'02-Compilation'/'QUALIFICATION-NATIVE-V31.0.ps1').read_text(encoding='utf-8')
    def test_windows_guard(self):
        self.assertIn("$env:OS -ne 'Windows_NT'",self.src)
    def test_artifact_checks(self):
        self.assertIn('verify-binary-artifacts.py',self.src)
        self.assertIn('verify-release.ps1',self.src)
    def test_extracted_portable(self):
        self.assertIn('Expand-Archive',self.src)
        self.assertIn('smoke-windows.ps1',self.src)
    def test_install_and_concurrency(self):
        self.assertIn('install-smoke-windows.ps1',self.src)
        self.assertIn('TEST-CONCURRENCE-WINDOWS.ps1',self.src)
    def test_failure_report(self):
        self.assertIn('FAIL |',self.src)
        self.assertIn('exit 1',self.src)
if __name__=='__main__': unittest.main()
