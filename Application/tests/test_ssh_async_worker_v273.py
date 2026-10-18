"""V27.3 regression: bridge preflight sees in-flight SSH work."""
import unittest
from concurrent.futures import Future
from ssh_async_worker import SSHAsyncWorker

class ManualExecutor:
    def __init__(self): self.future=Future();self.calls=0
    def submit(self, fn): self.calls+=1;return self.future

class Adapter:
    def cancel(self): pass
    def close(self): pass

class WorkerBusyStateTests(unittest.TestCase):
    def test_busy_until_future_finishes(self):
        executor=ManualExecutor(); worker=SSHAsyncWorker(Adapter(),executor=executor)
        self.assertFalse(worker.is_connecting)
        worker.connect()
        self.assertTrue(worker.is_connecting)
        with self.assertRaisesRegex(RuntimeError,'already in progress'): worker.connect()
        self.assertEqual(executor.calls,1)
        executor.future.set_result(None)
        self.assertFalse(worker.is_connecting)
        worker.close()
    def test_closed_worker_is_not_busy(self):
        executor=ManualExecutor();worker=SSHAsyncWorker(Adapter(),executor=executor)
        worker.connect();worker.close()
        self.assertFalse(worker.is_connecting)
        with self.assertRaisesRegex(RuntimeError,'worker closed'): worker.connect()

if __name__=='__main__':unittest.main()
