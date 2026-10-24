"""Regression for cancellation state and queue serialization. Author: Abdelhalim Talbi."""
import unittest
from threading import Event
from transfer_queue import TransferQueue

class Job:
    def __init__(self):
        self.cancel_event=Event()
    def cancel(self):
        self.cancel_event.set()

class QueueCancellationTests(unittest.TestCase):
    def test_cancel_active_waits_for_worker_then_records_cancelled(self):
        queue=TransferQueue()
        first=queue.submit(Job())
        second=queue.submit(Job())
        self.assertIs(queue.start_next(),first)
        queue.cancel_active()
        self.assertTrue(first['job'].cancel_event.is_set())
        self.assertIsNone(queue.start_next())
        queue.complete(first,False)
        self.assertEqual(first['state'],'cancelled')
        self.assertIs(queue.start_next(),second)
        queue.complete(second,True)
        self.assertEqual(second['state'],'done')

    def test_cancel_pending_records_cancelled(self):
        queue=TransferQueue()
        entry=queue.submit(Job())
        queue.cancel_pending()
        self.assertEqual(entry['state'],'cancelled')
        self.assertEqual(queue.history,[entry])
        self.assertIsNone(queue.start_next())

    def test_failure_without_cancellation_remains_failed(self):
        queue=TransferQueue()
        entry=queue.submit(Job())
        queue.start_next()
        queue.complete(entry,False)
        self.assertEqual(entry['state'],'failed')

    def test_success_after_cancellation_is_not_done(self):
        queue=TransferQueue()
        entry=queue.submit(Job())
        queue.start_next()
        queue.cancel_active()
        queue.complete(entry,True)
        self.assertEqual(entry['state'],'cancelled')

if __name__=='__main__':
    unittest.main()
