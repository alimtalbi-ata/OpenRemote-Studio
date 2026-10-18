import tempfile,unittest,sqlite3
from pathlib import Path
from session_history import SessionHistory
class SessionStatisticsTests(unittest.TestCase):
 def test_counts_outcomes(self):
  with tempfile.TemporaryDirectory() as d:
   h=SessionHistory(Path(d)/'db')
   for pid,code in [(1,0),(2,255),(3,None)]:
    row={'connection_id':'x','name':'Node','protocol':'SSH','pid':pid,'started_at':str(pid)}
    h.started(row)
    if code is not None:h.finished({**row,'status':'exited','exit_code':code})
   stats=h.statistics()[0]
   self.assertEqual((stats['attempts'],stats['success'],stats['failed'],stats['unobserved']),(3,1,1,1))
 def test_invalid_limit(self):
  with tempfile.TemporaryDirectory() as d:
   h=SessionHistory(Path(d)/'db')
   for limit in (0,-1,True,100001):
    with self.assertRaises(ValueError):h.statistics(limit)
 def test_connection_closes_after_exception(self):
  with tempfile.TemporaryDirectory() as d:
   h=SessionHistory(Path(d)/'db')
   with self.assertRaises(RuntimeError):
    with h._db() as db:
     db.execute('CREATE TABLE transient (id INTEGER)')
     raise RuntimeError('rollback')
   db=sqlite3.connect(str(h.path))
   try:
    self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='transient'").fetchone())
   finally:
    db.close()
 def test_grouping(self):
  with tempfile.TemporaryDirectory() as d:
   h=SessionHistory(Path(d)/'db')
   for cid in ('a','b'):
    h.started({'connection_id':cid,'name':cid,'protocol':'RDP','pid':1,'started_at':'t'})
   self.assertEqual(len(h.statistics()),2)
