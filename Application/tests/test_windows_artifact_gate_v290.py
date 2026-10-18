import pathlib, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'windows'
class WindowsArtifactGateV290(unittest.TestCase):
    def test_zip_entry_safety(self):
        code = (ROOT / 'build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('Unsafe portable ZIP path', code)
        self.assertIn('Duplicate portable ZIP path', code)
        self.assertIn('$entry.Open()', code)
    def test_setup_presence_gate(self):
        code = (ROOT / 'build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('Setup.exe is absent', code)
        self.assertIn('Setup.exe is suspiciously small', code)
    def test_single_entry_build(self):
        cmd = (ROOT / 'BUILD-WINDOWS.cmd').read_text(encoding='utf-8')
        self.assertIn('bootstrap-and-build.ps1', cmd)
