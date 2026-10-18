import tempfile, unittest
from pathlib import Path
from ssh_diagnostic_history import DiagnosticHistory
from ssh_history_integrity import create_export, verify_export

KEY=b'v11-test-key-' + b'x'*32
REPORT={'schema':'openremote.ssh-diagnostic.v1','status':'authenticated','steps':[{'step':'Bastion principal','state':'ok','duration_ms':41}]}
class SignedImportTests(unittest.TestCase):
    def test_import_preserves_timestamp_and_normalizes(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            records=[{'recorded_at':1234,'report':REPORT}]
            verified=verify_export(create_export(records,KEY),KEY)
            self.assertEqual(h.import_verified(verified),1)
            row=h.recent(1)[0]
            self.assertEqual(row['recorded_at'],1234)
            self.assertEqual(row['report']['status'],'authenticated')
    def test_import_rejects_noncanonical(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            with self.assertRaises(ValueError): h.import_verified([{'recorded_at':1,'report':{'password':'secret'}}])
            self.assertEqual(h.recent(1),[])
    def test_import_bound(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            with self.assertRaises(ValueError):h.import_verified([{'recorded_at':1,'report':REPORT}]*201)
    def test_atomic_import(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            rows=[{'recorded_at':1,'report':REPORT},{'recorded_at':-1,'report':REPORT}]
            with self.assertRaises(ValueError):h.import_verified(rows)
            self.assertEqual(h.recent(1),[])
if __name__=='__main__':unittest.main()
