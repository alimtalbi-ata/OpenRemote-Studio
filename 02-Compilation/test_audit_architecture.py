"""Tests for the static architecture inventory (no Qt dependency)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("audit_architecture.py")
spec = importlib.util.spec_from_file_location("audit_architecture", MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ArchitectureInventoryTests(unittest.TestCase):
    def test_counts_and_local_imports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            app = root / "Application"
            app.mkdir()
            (app / "first.py").write_text("import second\nclass C:\n    def f(self):\n        if True:\n            pass\n", encoding="utf-8")
            (app / "second.py").write_text("VALUE = 1\n", encoding="utf-8")
            result = audit.inventory(root)
            self.assertEqual(result["module_count"], 2)
            self.assertEqual(result["parse_errors"], [])
            self.assertIn(("second", 1), result["most_imported_local_modules"])
            self.assertEqual(result["hotspots"][0]["path"], "Application/first.py")

    def test_excludes_generated_and_reports_syntax_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            app = root / "Application"
            (app / ".venv-build").mkdir(parents=True)
            (app / ".venv-build" / "bad.py").write_text("def !!!", encoding="utf-8")
            (app / "broken.py").write_text("def !!!", encoding="utf-8")
            result = audit.inventory(root)
            self.assertEqual(result["module_count"], 0)
            self.assertEqual(len(result["parse_errors"]), 1)


if __name__ == "__main__":
    unittest.main()
