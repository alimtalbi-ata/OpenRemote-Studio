import tempfile,unittest
from pathlib import Path
from session_history import SessionHistory
from external_sessions import ExternalSessionRegistry
class Fake:
 def __init__(self):self.pid=42;self.code=None
 def poll(self):return self.code
class HistoryTests(unittest.TestCase):
 def test_persists_start_and_finish(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'sessions.db';h=SessionHistory(p);reg=ExternalSessionRegistry(h)
   proc=Fake();reg.register({'id':'a','name':'Alpha','protocol':'SSH'},proc)
   self.assertEqual(len(SessionHistory(p).recent()),1)
   proc.code=255;reg.snapshot()
   row=SessionHistory(p).recent()[0]
   self.assertEqual(row['exit_code'],255)
   self.assertIsNotNone(row['finished_at'])
 def test_idempotent_reconcile(self):
  with tempfile.TemporaryDirectory() as d:
   h=SessionHistory(Path(d)/'db');reg=ExternalSessionRegistry(h);p=Fake()
   reg.register({'id':'x','name':'X','protocol':'RDP'},p);p.code=0
   reg.snapshot();first=h.recent()[0]['finished_at'];reg.snapshot()
   self.assertEqual(h.recent()[0]['finished_at'],first)
 def test_no_secrets_stored(self):
  with tempfile.TemporaryDirectory() as d:
   h=SessionHistory(Path(d)/'db');reg=ExternalSessionRegistry(h)
   reg.register({'id':'x','name':'X','protocol':'SSH','password':'SENSITIVE','host':'hidden.example'},Fake())
   self.assertNotIn('password',str(h.recent()[0]))
   self.assertNotIn('hidden.example',str(h.recent()[0]))
 def test_limit_guard(self):
  with tempfile.TemporaryDirectory() as d:
   h=SessionHistory(Path(d)/'db')
   for n in (0,-1,1001,True):
    with self.assertRaises(ValueError):h.recent(n)
 def test_registry_survives_history_error(self):
  class Broken:
   def started(self,row):raise OSError('storage unavailable')
   def finished(self,row):raise OSError('storage unavailable')
  reg=ExternalSessionRegistry(Broken());p=Fake()
  reg.register({'id':'a','name':'A','protocol':'SSH'},p)
  p.code=1;reg.snapshot()
  self.assertEqual(len(reg.history_errors),2)
