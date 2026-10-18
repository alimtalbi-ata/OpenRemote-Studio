import tempfile
import unittest
from pathlib import Path
from protocol_readiness import MODULES, inspect_source, summary

class ReadinessTests(unittest.TestCase):
    def test_current_sources_parse(self):
        report = inspect_source(Path(__file__).resolve().parents[1])
        self.assertEqual(set(report), set(MODULES))
        self.assertTrue(all(item["source_ready"] for item in report.values()))
    def test_missing_is_not_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            report = inspect_source(folder)
            self.assertFalse(any(item["source_ready"] for item in report.values()))
            self.assertEqual(summary(report)["source_ready"], 0)
    def test_invalid_syntax(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for names in MODULES.values():
                for name in names: (root/name).write_text('pass\n')
            (root/'gateways.py').write_text('def bad(:\n')
            report=inspect_source(root)
            self.assertFalse(report['RDP']['source_ready'])
            self.assertFalse(report['VNC']['source_ready'])
            self.assertTrue(report['SSH']['source_ready'])
    def test_summary_rejects_partial(self):
        with self.assertRaises(ValueError): summary({})
    def test_no_hostnames_or_credentials(self):
        report=inspect_source(Path(__file__).resolve().parents[1])
        self.assertNotIn('password',str(report).lower())
        self.assertNotIn('hostname',str(report).lower())

if __name__=='__main__': unittest.main()
