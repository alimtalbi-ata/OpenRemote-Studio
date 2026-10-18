import json
import tempfile
import unittest
from pathlib import Path
from startup_diagnostics import diagnostics_path, record_startup, safe_record

class StartupDiagnosticsTests(unittest.TestCase):
    def test_path_isolated(self):
        self.assertEqual(diagnostics_path({'LOCALAPPDATA': 'C:/QA'}), Path('C:/QA/OpenRemoteStudio/diagnostics/startup.jsonl'))
    def test_appdata_fallback(self):
        self.assertEqual(diagnostics_path({'APPDATA': 'C:/Roaming'}), Path('C:/Roaming/OpenRemoteStudio/diagnostics/startup.jsonl'))
    def test_privacy_no_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'startup.jsonl'
            record_startup('main_window','failed',RuntimeError('SECRET-PASSWORD-XYZ'),p)
            data=p.read_text()
            self.assertNotIn('SECRET-PASSWORD-XYZ',data)
            self.assertEqual(json.loads(data)['error_type'],'RuntimeError')
    def test_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'startup.jsonl'
            record_startup('qt_init','ok',path=p)
            record_startup('main_window','ok',path=p)
            self.assertEqual(len(p.read_text().splitlines()),2)
    def test_invalid_stage(self):
        with self.assertRaises(ValueError):record_startup('password','ok')
    def test_invalid_outcome(self):
        with self.assertRaises(ValueError):record_startup('qt_init','unknown')
    def test_best_effort_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(safe_record('qt_init','ok',path=Path(tmp)))
    def test_gui_integration(self):
        text=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn("safe_record('main_window', 'failed', exc)",text)
        self.assertIn("safe_record('qt_init', 'failed', exc)",text)
