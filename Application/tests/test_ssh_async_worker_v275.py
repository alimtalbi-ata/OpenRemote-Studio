"""V27.5: failed submission does not poison the connection state."""
import unittest
from concurrent.futures import Future
from ssh_async_worker import SSHAsyncWorker

class RejectOnce:
    def __init__(self): self.calls=0; self.future=Future()
    def submit(self, fn):
        self.calls += 1
        if self.calls == 1: raise RuntimeError('executor unavailable')
        return self.future

class Adapter:
    def cancel(self): pass
    def close(self): pass

class SubmitRecoveryTests(unittest.TestCase):
    def test_retry_after_executor_rejection(self):
        executor=RejectOnce(); worker=SSHAsyncWorker(Adapter(), executor=executor)
        with self.assertRaisesRegex(RuntimeError, 'executor unavailable'):
            worker.connect()
        self.assertFalse(worker.is_connecting)
        self.assertIsNone(worker._future)
        self.assertIs(worker.connect(), executor.future)
        self.assertTrue(worker.is_connecting)
        worker.close()

    def test_closed_worker_does_not_submit(self):
        executor=RejectOnce(); worker=SSHAsyncWorker(Adapter(), executor=executor)
        worker.close()
        with self.assertRaisesRegex(RuntimeError, 'worker closed'):
            worker.connect()
        self.assertEqual(executor.calls, 0)
