import tempfile
import unittest
from pathlib import Path
from ssh_diagnostic_history import DiagnosticHistory

REPORT={'schema':'openremote.ssh-diagnostic.v1','status':'authenticated','steps':[{'step':'Bastion principal','state':'ok','duration_ms':41}]}

def row(ts=1234): return {'recorded_at':ts,'report':REPORT}

class ImportPreviewV111Tests(unittest.TestCase):
    def test_preview_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            self.assertEqual(h.preview_import([row()]),{'total':1,'new':1,'duplicates':0})
            self.assertEqual(h.recent(1),[])
    def test_existing_duplicate_detected_and_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            h.import_verified([row()])
            self.assertEqual(h.preview_import([row()]),{'total':1,'new':0,'duplicates':1})
            self.assertEqual(h.import_verified([row()]),0)
            self.assertEqual(len(h.recent(20)),1)
    def test_duplicates_inside_same_file_counted_once(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            self.assertEqual(h.preview_import([row(),row()]),{'total':2,'new':1,'duplicates':1})
            self.assertEqual(h.import_verified([row(),row()]),1)
            self.assertEqual(len(h.recent(20)),1)
    def test_timestamp_is_part_of_identity(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            h.import_verified([row(1234)])
            self.assertEqual(h.preview_import([row(1235)]),{'total':1,'new':1,'duplicates':0})
    def test_invalid_preview_does_not_write(self):
        with tempfile.TemporaryDirectory() as td:
            h=DiagnosticHistory(Path(td)/'h.db')
            with self.assertRaises(ValueError): h.preview_import([{'recorded_at':-1,'report':REPORT}])
            self.assertEqual(h.recent(1),[])

if __name__=='__main__': unittest.main()
