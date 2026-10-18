import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class WindowsSingleExeContract(unittest.TestCase):
    def test_spec_embeds_binaries_and_data(self):
        s=(ROOT/'windows/OpenRemoteStudio-onefile.spec').read_text()
        self.assertIn('EXE(pyz, a.scripts, a.binaries, a.datas',s)
        self.assertNotIn('COLLECT(',s)
    def test_builder_switch_propagates(self):
        for name in ('bootstrap-and-build.ps1','build-windows.ps1','verify-release.ps1'):
            self.assertIn('[switch]$SingleExe',(ROOT/'windows'/name).read_text())
    def test_installer_supports_both_layouts(self):
        s=(ROOT/'windows/OpenRemoteStudio.iss').read_text()
        self.assertIn('#ifdef SingleExeBuild',s)
        self.assertIn('dist\\OpenRemoteStudio.exe',s)
        self.assertIn('dist\\OpenRemoteStudio\\*',s)
        self.assertIn('version.generated.iss',s)
    def test_portable_onefile_contains_only_exe(self):
        s=(ROOT/'windows/build-windows.ps1').read_text()
        self.assertIn('Compress-Archive -LiteralPath',s)
        self.assertIn('OpenRemoteStudio-onefile.spec',s)
    def test_smoke_runs_for_both_modes(self):
        s=(ROOT/'windows/build-windows.ps1').read_text()
        self.assertIn('smoke-windows.ps1',s)
        self.assertIn('-Exe $exe',s)
