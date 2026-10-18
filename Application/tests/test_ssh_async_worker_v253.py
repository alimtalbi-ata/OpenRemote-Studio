import unittest
from threading import Event
from ssh_async_worker import SSHAsyncWorker
from guarded_ssh_adapter import GuardedSSHAdapter

class Resource:
    def __init__(self): self.closed=False
    def close(self): self.closed=True

class Tests(unittest.TestCase):
    def test_success(self):
        r=Resource(); worker=SSHAsyncWorker(GuardedSSHAdapter('one',lambda:r)); self.assertIs(worker.connect().result(3),r);worker.close();self.assertTrue(r.closed)
    def test_error(self):
        errors=[]
        def fail(): raise OSError('offline')
        worker=SSHAsyncWorker(GuardedSSHAdapter('two',fail)); self.assertIsNone(worker.connect(on_error=errors.append).result(3));self.assertIsInstance(errors[0],OSError);worker.close()
    def test_cancel_late_result(self):
        entered=Event(); release=Event();r=Resource();errors=[]
        def connect(): entered.set();release.wait(3);return r
        worker=SSHAsyncWorker(GuardedSSHAdapter('three',connect));f=worker.connect(on_error=errors.append);self.assertTrue(entered.wait(2));worker.cancel();release.set();f.result(3);self.assertTrue(r.closed);self.assertTrue(errors);worker.close()
    def test_no_duplicate_connect(self):
        entered=Event();release=Event()
        def connect(): entered.set();release.wait(3);return Resource()
        worker=SSHAsyncWorker(GuardedSSHAdapter('four',connect));f=worker.connect();self.assertTrue(entered.wait(2))
        with self.assertRaises(RuntimeError):worker.connect()
        release.set();f.result(3);worker.close()
    def test_closed_worker(self):
        worker=SSHAsyncWorker(GuardedSSHAdapter('five',Resource));worker.close()
        with self.assertRaises(RuntimeError):worker.connect()
if __name__=='__main__': unittest.main()
