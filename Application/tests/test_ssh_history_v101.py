"""History filters, trends and retention. Author Abdelhalim Talbi."""
import tempfile,unittest,sqlite3
from contextlib import closing
from pathlib import Path
from ssh_diagnostic_history import DiagnosticHistory,duration_series

def report(state='authenticated',ms=100):
    return {'schema':'openremote.ssh-diagnostic.v1','status':state,'steps':[{'step':'Bastion principal','state':'ok' if state=='authenticated' else 'failed','duration_ms':ms}]}

class TestHistoryV101(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.history=DiagnosticHistory(Path(self.tmp.name)/'history.db')
        self.history.add(report());self.history.add(report('failed',300))
        with closing(sqlite3.connect(self.history.path)) as db, db:
            db.execute('UPDATE diagnostics SET recorded_at=100 WHERE id=1')
            db.execute('UPDATE diagnostics SET recorded_at=200 WHERE id=2')
    def test_status(self):self.assertEqual(len(self.history.filtered(status='failed')),1)
    def test_since(self):self.assertEqual(self.history.filtered(since=150)[0]['recorded_at'],200)
    def test_until(self):self.assertEqual(self.history.filtered(until=150)[0]['recorded_at'],100)
    def test_range(self):self.assertEqual(len(self.history.filtered(since=101,until=199)),0)
    def test_invalid(self):
        for kwargs in ({'limit':201},{'since':-1},{'since':300,'until':200},{'status':'bad'}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.history.filtered(**kwargs)
    def test_purge(self):
        self.assertEqual(self.history.purge_before(150),1)
        self.assertEqual(len(self.history.recent()),1)
    def test_purge_invalid(self):
        with self.assertRaises(ValueError):self.history.purge_before(-1)
    def test_series(self):
        data=duration_series(self.history.recent(),limit=2)
        self.assertEqual([x['duration_ms'] for x in data],[100,300])
    def test_series_step_validation(self):
        with self.assertRaises(ValueError):duration_series(self.history.recent(),step='server-secret')
    def test_series_limit(self):self.assertEqual(len(duration_series(self.history.recent(),limit=1)),1)
