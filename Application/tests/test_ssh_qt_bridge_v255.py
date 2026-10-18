import os
import unittest
from concurrent.futures import Future
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import QCoreApplication
    from ssh_qt_bridge import SSHQtBridge
except ImportError:
    SSHQtBridge = None

class FakeWorker:
    def connect(self, on_success, on_error):
        self.ok, self.err = on_success, on_error
        f = Future(); f.set_result(None); return f
    def cancel(self): return None
    def close(self): return None

class Resource:
    def __init__(self): self.closed = False
    def close(self): self.closed = True

@unittest.skipIf(SSHQtBridge is None, 'PySide6 unavailable')
class BridgeV255Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QCoreApplication.instance() or QCoreApplication([])
    def test_cancel_closes_late_resource(self):
        w=FakeWorker(); b=SSHQtBridge(w); b.start(); old=w.ok; b.cancel()
        r=Resource(); old(r); self.app.processEvents(); self.assertTrue(r.closed)
    def test_close_suppresses_late_error(self):
        w=FakeWorker(); b=SSHQtBridge(w); got=[]; b.failed.connect(got.append)
        b.start(); old=w.err; b.close(); old(OSError('offline')); self.app.processEvents(); self.assertEqual(got,[])
    def test_new_attempt_rejects_previous_result(self):
        w=FakeWorker(); b=SSHQtBridge(w); b.start(); old=w.ok
        b.start(); r=Resource(); old(r); self.app.processEvents(); self.assertTrue(r.closed); b.close()

if __name__=='__main__': unittest.main()
