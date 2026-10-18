import tempfile,unittest
from pathlib import Path
from transfer_journal import TransferJournal
class JournalTests(unittest.TestCase):
 def test_lifecycle(self):
  with tempfile.TemporaryDirectory() as d:
   j=TransferJournal(Path(d)/'journal.sqlite3')
   i=j.add('server-1','download','/remote/a','C:/temp/a')
   j.update(i,'running',30)
   self.assertEqual(j.recent()[0][5:],('running',30))
   j.update(i,'done',100)
   self.assertEqual(j.recent()[0][5],'done')
   j.close()
 def test_restart_marks_incomplete(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'j.db';j=TransferJournal(path)
   i=j.add('s','upload','/remote','local')
   j.update(i,'running',20);j.close()
   j=TransferJournal(path)
   self.assertEqual(j.recent()[0][5],'interrupted')
   j.close()
 def test_no_auto_replay(self):
  with tempfile.TemporaryDirectory() as d:
   j=TransferJournal(Path(d)/'j.db')
   j.add('s','download','/x','/y');j.close()
   j=TransferJournal(Path(d)/'j.db')
   self.assertEqual(j.recent()[0][5],'interrupted')
   j.close()
 def test_reject_bad_progress(self):
  with tempfile.TemporaryDirectory() as d:
   j=TransferJournal(Path(d)/'j.db');i=j.add('s','download','/x','/y')
   with self.assertRaises(ValueError):j.update(i,'running',101)
   j.close()
 def test_reject_unknown_kind(self):
  with tempfile.TemporaryDirectory() as d:
   j=TransferJournal(Path(d)/'j.db')
   with self.assertRaises(ValueError):j.add('s','delete','/x','/y')
   j.close()
