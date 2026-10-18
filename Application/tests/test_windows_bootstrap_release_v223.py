"""Current release contract, replacing V22 legacy path assumptions."""
import importlib.util, tempfile, unittest, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('current_release_gate',ROOT/'VERIFY-RELEASE.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class CurrentReleaseContract(unittest.TestCase):
 def test_tree_valid(self): self.assertEqual([],gate.validate(ROOT))
 def test_missing_required_rejected(self):
  with tempfile.TemporaryDirectory() as d:self.assertTrue(gate.validate(d))
 def test_bad_archive_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.zip';p.write_bytes(b'bad');self.assertTrue(gate.validate_archive(p))
 def test_windows_build_uses_gate(self):
  self.assertIn('VERIFY-RELEASE.py',(ROOT/'02-Compilation/QUALIFIER-ET-CONSTRUIRE-WINDOWS.cmd').read_text())
