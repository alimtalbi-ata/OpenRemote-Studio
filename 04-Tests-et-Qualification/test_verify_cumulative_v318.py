"""Unit tests for V31.8 cumulative archive verification."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "02-Compilation" / "verify_cumulative_v318.py"
spec = importlib.util.spec_from_file_location("verifier", SCRIPT)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

class ArchiveTests(unittest.TestCase):
    def make_zip(self, directory, extra=(), provenance=True):
        target = Path(directory) / "test.zip"
        with zipfile.ZipFile(target, "w") as archive:
            for prefix in verifier.REQUIRED:
                archive.writestr(prefix + "placeholder.txt", "sample")
            if provenance:
                archive.writestr("07-Manifestes/provenance.json", json.dumps({
                    "commit": "a" * 40, "windows_build_run": "123"
                }))
            for name in extra:
                archive.writestr(name, "x")
        return target

    def test_valid_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(verifier.verify(self.make_zip(tmp), "a" * 40)["status"], "PASS")

    def test_wrong_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = verifier.verify(self.make_zip(tmp), "b" * 40)
            self.assertIn("source commit mismatch", result["errors"])

    def test_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = verifier.verify(self.make_zip(tmp, ["../evil.txt"]))
            self.assertTrue(any("unsafe ZIP path" in error for error in result["errors"]))

    def test_missing_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = verifier.verify(self.make_zip(tmp, provenance=False))
            self.assertIn("missing provenance.json", result["errors"])

if __name__ == "__main__":
    unittest.main()
