import tempfile,unittest
from pathlib import Path
from ssh_diagnostic_history import DiagnosticHistory,normalize,trends

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.history=DiagnosticHistory(Path(self.tmp.name)/'history.sqlite3')
        self.report={'schema':'openremote.ssh-diagnostic.v1','status':'authenticated','host':'SECRET.EXAMPLE','username':'admin',
                     'steps':[{'step':'Bastion principal','state':'ok','duration_ms':100,'password':'SECRET'},
                              {'step':'Serveur cible','state':'ok','duration_ms':200}]}
    def test_save_read(self):
        self.history.add(self.report);self.assertEqual(len(self.history.recent()),1)
    def test_redaction(self):
        self.history.add(self.report)
        self.assertNotIn('SECRET',str(self.history.recent()))
        self.assertNotIn('admin',str(self.history.recent()))
    def test_reopen(self):
        self.history.add(self.report);self.assertEqual(len(DiagnosticHistory(self.history.path).recent()),1)
    def test_clear(self):
        self.history.add(self.report);self.history.clear();self.assertEqual(self.history.recent(),[])
    def test_limit(self):
        with self.assertRaises(ValueError):self.history.recent(201)
    def test_trends(self):
        self.history.add(self.report);self.history.add(self.report)
        data=trends(self.history.recent());self.assertEqual(data[0]['average_ms'],100)
    def test_reject_bad_step(self):
        self.report['steps'][0]['step']='SECRET HOST'
        with self.assertRaises(ValueError):self.history.add(self.report)
    def test_reject_bad_duration(self):
        self.report['steps'][0]['duration_ms']=-1
        with self.assertRaises(ValueError):self.history.add(self.report)
    def test_bounded_retention(self):
        for _ in range(205):self.history.add(self.report)
        self.assertEqual(len(self.history.recent(200)),200)
    def test_empty_trends(self):self.assertEqual(trends([]),[])
