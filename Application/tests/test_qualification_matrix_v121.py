import json
import tempfile
import unittest
from pathlib import Path
from qualification_matrix import SCENARIOS, build_matrix, write_report

ROOT = Path(__file__).resolve().parents[1]

class QualificationMatrixTests(unittest.TestCase):
    def test_scenarios_are_unique(self):
        self.assertEqual(len({row[0] for row in SCENARIOS}), len(SCENARIOS))
    def test_coverage(self):
        self.assertEqual({r[2] for r in SCENARIOS}, {'Windows','SSH','RDP','VNC','SFTP','PAM'})
    def test_no_false_pass(self):
        report = build_matrix(ROOT)
        self.assertTrue(all(r['status']=='not_executed' for r in report['scenarios']))
    def test_no_live_tests_claimed(self):
        report = build_matrix(ROOT)
        self.assertEqual(report['live_tests_executed'], 0)
        self.assertEqual(report['gui_tests_executed'], 0)
    def test_source_inventory(self):
        report = build_matrix(ROOT)
        self.assertTrue(report['source_inventory']['SSH']['source_ready'])
    def test_write_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'matrix.json'
            write_report(ROOT,p)
            self.assertEqual(json.loads(p.read_text())['schema'],'openremote-qualification-v1')
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'matrix.json'
            write_report(ROOT,p)
            with self.assertRaises(FileExistsError):write_report(ROOT,p)
    def test_no_secrets_in_report(self):
        report=build_matrix(ROOT)
        self.assertNotIn('private_key',json.dumps(report))
