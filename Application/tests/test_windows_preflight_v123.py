import tempfile
import unittest
from pathlib import Path
from windows_preflight import assess, write_report

class WindowsPreflightTests(unittest.TestCase):
    def test_windows_ready(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"app.py").write_text("pass")
            r=assess(d,system="Windows",find_spec=lambda m: object())
            self.assertTrue(r["ready_to_attempt_gui_launch"])
            self.assertFalse(r["gui_launch_executed"])
    def test_linux_not_ready(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"app.py").touch()
            self.assertFalse(assess(d,system="Linux",find_spec=lambda m: object())["ready_to_attempt_gui_launch"])
    def test_missing_required(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"app.py").touch()
            self.assertFalse(assess(d,system="Windows",find_spec=lambda m: None)["ready_to_attempt_gui_launch"])
    def test_optional_not_blocking(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"app.py").touch()
            r=assess(d,system="Windows",find_spec=lambda m: object() if m=="PySide6" else None)
            self.assertTrue(r["ready_to_attempt_gui_launch"])
    def test_missing_entry(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(assess(d,system="Windows",find_spec=lambda m: object())["ready_to_attempt_gui_launch"])
    def test_exclusive_report(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"report.json"
            write_report(d,path)
            with self.assertRaises(FileExistsError): write_report(d,path)
