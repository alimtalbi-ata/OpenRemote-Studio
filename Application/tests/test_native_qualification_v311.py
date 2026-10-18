import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class NativeQualification311(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.script=(ROOT/'02-Compilation/QUALIFICATION-NATIVE-V31.1.ps1').read_text(encoding='utf-8')
    def test_json_report(self): self.assertIn('ConvertTo-Json -Depth 5',self.script); self.assertIn("ChangeExtension($report, '.json')",self.script)
    def test_child_exit_status(self): self.assertGreaterEqual(self.script.count('$LASTEXITCODE -ne 0'),5)
    def test_steps_and_skips(self): self.assertIn('skipped = @(',self.script); self.assertIn('steps = @($records.ToArray())',self.script)
    def test_release_version(self): self.assertIn("-ne '31.1'",self.script)
