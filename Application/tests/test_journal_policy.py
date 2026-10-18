import unittest
from journal_policy import progress_or_cancel,terminal_audit
class Job:
 def __init__(self):self.cancelled=False
 def cancel(self):self.cancelled=True
class Journal:
 def __init__(self,broken=False):self.broken=broken;self.events=[]
 def update(self,*args):
  if self.broken:raise OSError('database unavailable')
  self.events.append(args)
class PolicyTests(unittest.TestCase):
 def test_progress_committed(self):
  j=Journal();job=Job();progress_or_cancel(j,job,4,55)
  self.assertEqual(j.events,[(4,'running',55)])
  self.assertFalse(job.cancelled)
 def test_progress_failure_cancels(self):
  job=Job()
  with self.assertRaises(OSError):progress_or_cancel(Journal(True),job,4,55)
  self.assertTrue(job.cancelled)
 def test_terminal_failure_is_not_success(self):
  with self.assertRaises(OSError):terminal_audit(Journal(True),4,'done',100)
 def test_terminal_success(self):
  j=Journal();self.assertTrue(terminal_audit(j,4,'done',100))
  self.assertEqual(j.events,[(4,'done',100)])
