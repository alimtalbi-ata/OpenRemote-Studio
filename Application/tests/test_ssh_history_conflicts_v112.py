import tempfile,unittest
from pathlib import Path
from ssh_diagnostic_history import DiagnosticHistory
from ssh_history_integrity import create_export,verify_export

REPORT={'schema':'openremote.ssh-diagnostic.v1','status':'authenticated','steps':[]}
FAILED={'schema':'openremote.ssh-diagnostic.v1','status':'failed','steps':[]}
class TestImportConflicts(unittest.TestCase):
 def test_conflict_and_audit(self):
  with tempfile.TemporaryDirectory() as td:
   db=DiagnosticHistory(Path(td)/'h.db')
   rows=[{'recorded_at':123,'report':REPORT},{'recorded_at':123,'report':FAILED},{'recorded_at':123,'report':REPORT}]
   verified=verify_export(create_export(rows,b'x'*32),b'x'*32)
   preview=db.preview_import(verified)
   preview.update(db.preview_import_details(verified))
   self.assertEqual((preview['new'],preview['duplicates'],preview['timestamp_conflicts']),(2,1,1))
   self.assertEqual(len(preview['sample']),2)
   self.assertEqual(db.import_verified(verified),2)
   self.assertEqual(db.import_verified(verified),0)
   self.assertEqual(db.import_audit()[0]['duplicates'],3)
   self.assertEqual(db.import_audit()[1]['conflicts'],1)
 def test_limit(self):
  with tempfile.TemporaryDirectory() as td:
   db=DiagnosticHistory(Path(td)/'h.db')
   for invalid in (0,101,True):
    with self.assertRaises(ValueError):db.import_audit(invalid)
