import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class EmbeddedRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verify = (ROOT/'windows/verify-release.ps1').read_text(encoding='utf8')
        cls.build = (ROOT/'windows/build-windows.ps1').read_text(encoding='utf8')
    def test_qt_plugin_in_zip(self): self.assertIn('platforms/qwindows', self.verify)
    def test_python_runtime_in_zip(self): self.assertIn('python3[0-9]+', self.verify)
    def test_qt_plugin_in_dist(self): self.assertIn("'qwindows.dll'", self.build)
    def test_python_runtime_in_dist(self): self.assertIn("'python3*.dll'", self.build)
    def test_checks_before_portable(self): self.assertIn('if ($SingleExe)', self.build); self.assertIn('if ($qtPlugin.Count -ne 1)', self.build)
    def test_no_implicit_install(self): self.assertNotIn('winget install', self.verify)
