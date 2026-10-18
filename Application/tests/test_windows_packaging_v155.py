import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class WindowsPackagingTests(unittest.TestCase):
    def test_spec_has_real_qt_entrypoint(self):
        s=(ROOT/'windows/OpenRemoteStudio.spec').read_text(encoding='utf-8')
        self.assertIn("root / 'qt_app.py'",s)
        self.assertIn("console=False",s)
    def test_inno_installs_per_user(self):
        s=(ROOT/'windows/OpenRemoteStudio.iss').read_text(encoding='utf-8')
        self.assertIn('PrivilegesRequired=lowest',s)
        self.assertIn('recursesubdirs',s)
        self.assertIn('[Icons]',s)
    def test_build_checks_failures_and_hashes(self):
        s=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('if ($LASTEXITCODE -ne 0)',s)
        self.assertIn('SHA256SUMS.txt',s)
        self.assertIn('PyInstaller',s)
    def test_smoke_checks_exe(self):
        s=(ROOT/'windows/smoke-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('--smoke-gui',s)
        self.assertIn('$process.ExitCode',s)
if __name__=='__main__':unittest.main()
