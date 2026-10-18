import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("release_preflight",ROOT/"02-Compilation"/"release_preflight.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ReleasePreflightTests(unittest.TestCase):
    def test_missing_files_block(self):
        with tempfile.TemporaryDirectory() as d:
            code,message=module.check(d,qt_available=True)
            self.assertEqual(code,2);self.assertIn("missing",message)
    def test_missing_qt_blocks(self):
        code,message=module.check(ROOT,qt_available=False)
        self.assertEqual(code,3);self.assertIn("PySide6",message)
    def test_present_qt_allows_next_gate(self):
        code,message=module.check(ROOT,qt_available=True)
        self.assertEqual(code,0);self.assertIn("READY",message)
if __name__=="__main__":unittest.main()
