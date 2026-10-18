import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class Release156(unittest.TestCase):
    def test_gui_smoke_explicit(self):
        s=(ROOT/'qt_app.py').read_text(encoding='utf8')
        self.assertIn("'--smoke-gui' in sys.argv",s)
        self.assertIn('QTimer.singleShot(1500, app.quit)',s)
    def test_build_runs_packaged_exe(self):
        s=(ROOT/'windows/build-windows.ps1').read_text(encoding='utf8')
        self.assertIn("'smoke-windows.ps1'",s)
        self.assertIn("-TimeoutSeconds 30",s)
    def test_smoke_isolated(self):
        s=(ROOT/'windows/smoke-windows.ps1').read_text(encoding='utf8')
        self.assertIn('$env:APPDATA = Join-Path $smokeRoot',s)
        self.assertIn('Remove-Item -LiteralPath $smokeRoot -Recurse -Force',s)
    def test_release_number(self):
        for f in ('windows/OpenRemoteStudio.iss','windows/build-windows.ps1'):
            self.assertIn('releaseVersion' if f.endswith('.ps1') else 'MyAppVersion',(ROOT/f).read_text(encoding='utf8'))
