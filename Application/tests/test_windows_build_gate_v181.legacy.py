import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class BuildGateV181Tests(unittest.TestCase):
    def test_bootstrap_exits_failure_after_finally(self):
        s=(ROOT/'windows/bootstrap-and-build.ps1').read_text(encoding='utf-8')
        self.assertIn('if ($script:buildFailed) { exit 1 }',s)
        self.assertIn('finally { Stop-Transcript | Out-Null }',s)
    def test_bootstrap_exits_success(self):
        self.assertIn('exit 0',(ROOT/'windows/bootstrap-and-build.ps1').read_text(encoding='utf-8'))
    def test_stale_portable_is_removed(self):
        s=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('Remove-Item -Force',s)
        self.assertIn('Portable\\.zip',s)
    def test_manifest_is_removed_before_build(self):
        s=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf-8')
        self.assertLess(s.index("'SHA256SUMS.txt' } | Remove-Item"),s.index('PyInstaller'))
    def test_one_click_entry(self):
        self.assertIn('bootstrap-and-build.ps1',(ROOT/'windows/BUILD-WINDOWS.cmd').read_text())
