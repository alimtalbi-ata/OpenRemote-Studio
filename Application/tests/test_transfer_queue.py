
import unittest
from transfer_queue import TransferQueue
class FakeJob:
 def __init__(self):self.cancelled=False
 def cancel(self):self.cancelled=True
class QueueTests(unittest.TestCase):
 def test_fifo(self):
  q=TransferQueue();a=q.submit(FakeJob());b=q.submit(FakeJob())
  self.assertIs(q.start_next(),a)
  self.assertIsNone(q.start_next())
  q.complete(a,True)
  self.assertIs(q.start_next(),b)
 def test_progress_clamped(self):
  q=TransferQueue();a=q.submit(FakeJob());q.start_next()
  q.progress(a,150);self.assertEqual(a['progress'],100)
  with self.assertRaises(ValueError):q.progress(a,-1)
  self.assertEqual(a['progress'],100)
 def test_cancel_pending(self):
  q=TransferQueue();a=q.submit(FakeJob());b=q.submit(FakeJob())
  q.start_next();q.cancel_pending()
  self.assertEqual(b['state'],'cancelled')
  self.assertEqual(a['state'],'running')
 def test_cancel_active(self):
  q=TransferQueue();a=q.submit(FakeJob());q.start_next()
  q.cancel_active();self.assertTrue(a['job'].cancelled)
 def test_failed_job_allows_next(self):
  q=TransferQueue();a=q.submit(FakeJob());b=q.submit(FakeJob())
  q.start_next();q.complete(a,False)
  self.assertEqual(a['state'],'failed')
  self.assertIs(q.start_next(),b)
 def test_no_duplicate_completion(self):
  q=TransferQueue();a=q.submit(FakeJob());q.start_next();q.complete(a,True)
  with self.assertRaises(ValueError):q.complete(a,True)

 def test_progress_rejects_bool_and_fraction(self):
  q=TransferQueue();a=q.submit(FakeJob());q.start_next()
  for value in (True,False,4.5,'10'):
   with self.subTest(value=value),self.assertRaises(ValueError):q.progress(a,value)
  self.assertEqual(a['progress'],0)
 def test_cancel_keeps_active_until_worker_finishes(self):
  q=TransferQueue();a=q.submit(FakeJob());b=q.submit(FakeJob());q.start_next()
  q.cancel_active();self.assertIsNone(q.start_next())
  q.complete(a,False);self.assertIs(q.start_next(),b)
 def test_complete_rejects_non_boolean(self):
  q=TransferQueue();a=q.submit(FakeJob());q.start_next()
  with self.assertRaises(ValueError):q.complete(a,1)
  self.assertIs(q.active,a)

 def test_confirmed_cancellation_is_terminal_and_releases_slot(self):
  q=TransferQueue();a=q.submit(FakeJob());b=q.submit(FakeJob());q.start_next()
  q.cancel_active()
  self.assertIs(q.active,a)
  q.complete_cancelled(a)
  self.assertEqual(a["state"],"cancelled")
  self.assertIsNone(q.active)
  self.assertIs(q.history[-1],a)
  self.assertIs(q.start_next(),b)

 def test_confirmed_cancellation_requires_active_entry(self):
  q=TransferQueue();a=q.submit(FakeJob())
  with self.assertRaises(ValueError):q.complete_cancelled(a)
  self.assertEqual(a["state"],"waiting")
