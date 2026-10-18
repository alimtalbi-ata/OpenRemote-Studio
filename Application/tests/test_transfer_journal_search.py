import tempfile,unittest
from pathlib import Path
from transfer_journal import TransferJournal
class JournalSearchTests(unittest.TestCase):
 def test_filter_state_and_connection(self):
  with tempfile.TemporaryDirectory() as d:
   j=TransferJournal(Path(d)/'j.db');a=j.add('a','download','/x','/y');b=j.add('b','upload','/z','/t');j.update(a,'done',100)
   self.assertEqual(len(j.search(state='done')),1)
   self.assertEqual(j.search(connection_id='a')[0][0],a)
   self.assertEqual(j.search(state='done',connection_id='b'),[])
   self.assertEqual(j.search()[0][0],b);j.close()
 def test_invalid_state(self):
  with tempfile.TemporaryDirectory() as d:
   j=TransferJournal(Path(d)/'j.db')
   with self.assertRaises(ValueError):j.search(state="done' OR 1=1 --")
   j.close()
 def test_invalid_limit(self):
  with tempfile.TemporaryDirectory() as d:
   j=TransferJournal(Path(d)/'j.db')
   with self.assertRaises(ValueError):j.search(limit=10000)
   j.close()
