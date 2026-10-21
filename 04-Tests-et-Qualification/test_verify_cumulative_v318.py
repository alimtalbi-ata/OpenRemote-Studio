"""V31.8 release archive verifier regression tests."""
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
    def make_zip(self, directory, extra=(), provenance=True, commit="a" * 40):
        target = Path(directory) / "test.zip"
        with zipfile.ZipFile(target, "w") as archive:
            for prefix in verifier.REQUIRED:
                archive.writestr(prefix + "placeholder.txt", "sample")
            if provenance:
                archive.writestr("07-Manifestes/provenance.json", json.dumps({
                    "commit": commit, "windows_build_run": "123"
                }))
            for name in extra:
                archive.writestr(name, "x")
        return target

    def test_valid_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(verifier.verify(self.make_zip(tmp), "a" * 40)["status"], "PASS")

    def test_wrong_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("source commit mismatch", verifier.verify(
                self.make_zip(tmp), "b" * 40)["errors"])

    def test_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = verifier.verify(self.make_zip(tmp, ["../evil.txt"]))["errors"]
            self.assertTrue(any("unsafe ZIP path" in e for e in errors))

    def test_missing_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("missing provenance.json",
                          verifier.verify(self.make_zip(tmp, provenance=False))["errors"])

    def test_invalid_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("invalid provenance commit",
                          verifier.verify(self.make_zip(tmp, commit="not-a-sha"))["errors"])

    def test_missing_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(verifier.verify(Path(tmp) / "missing.zip")["status"], "FAIL")

    def test_corrupt_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bad.zip"
            target.write_bytes(b"not a zip")
            self.assertEqual(verifier.verify(target)["status"], "FAIL")

    def test_case_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = verifier.verify(self.make_zip(tmp, ["README", "readme"]))["errors"]
            self.assertIn("case-insensitive ZIP name collision", errors)

if __name__ == "__main__":
    unittest.main()
