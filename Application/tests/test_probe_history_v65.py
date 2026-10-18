import tempfile,unittest
from pathlib import Path
from probe_history import ProbeHistory,classify_ssh_result
class TestProbeHistory(unittest.TestCase):
    def test_persist_and_filter(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'probes.sqlite3';h=ProbeHistory(p)
            h.add('one','ssh_jump','unknown');h.add('two','tcp_local','failed')
            self.assertEqual(len(ProbeHistory(p).recent()),2)
            self.assertEqual(len(h.recent('one')),1)
            self.assertEqual(h.recent('one')[0][2],'unknown')
    def test_invalid_fields(self):
        with tempfile.TemporaryDirectory() as d:
            h=ProbeHistory(Path(d)/'p.db')
            for kind,outcome in [('bad','ok'),('ssh_jump','password=secret')]:
                with self.assertRaises(ValueError):h.add('one',kind,outcome)
    def test_limit(self):
        with tempfile.TemporaryDirectory() as d:
            h=ProbeHistory(Path(d)/'p.db')
            with self.assertRaises(ValueError):h.recent(limit=501)
    def test_ssh_classification(self):
        self.assertEqual(classify_ssh_result('Permission denied'), 'failed')
        self.assertEqual(classify_ssh_result('Process exited with code 0'), 'unknown')
    def test_ui_wiring(self):
        text=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('Historique diagnostics',text)
        self.assertIn('self._record_ssh_probe(identity,message,result)',text)
