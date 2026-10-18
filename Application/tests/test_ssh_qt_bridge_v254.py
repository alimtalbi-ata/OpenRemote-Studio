import os
import unittest
from concurrent.futures import Future

try:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import QCoreApplication
    from ssh_qt_bridge import SSHQtBridge
except ImportError:
    SSHQtBridge = None

class FakeWorker:
    def __init__(self): self.calls=0; self.closed=False; self.cancelled=False
    def connect(self,on_success=None,on_error=None):
        self.calls+=1; self.ok=on_success; self.err=on_error
        f=Future();f.set_result(None);return f
    def cancel(self): self.cancelled=True
    def close(self): self.closed=True

@unittest.skipIf(SSHQtBridge is None, 'PySide6 unavailable')
class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QCoreApplication.instance() or QCoreApplication([])
    def test_success_signal(self):
        w=FakeWorker();b=SSHQtBridge(w);received=[];b.connected.connect(received.append)
        b.start();token=object();w.ok(token)
        self.assertEqual(received,[])
        self.app.processEvents()
        self.assertEqual(received,[token]);b.close()
    def test_error_signal(self):
        w=FakeWorker();b=SSHQtBridge(w);received=[];b.failed.connect(received.append)
        b.start();w.err(OSError('offline'))
        self.assertEqual(received,[])
        self.app.processEvents()
        self.assertEqual(received,['OSError: offline']);b.close()
    def test_cancel_and_close(self):
        w=FakeWorker();b=SSHQtBridge(w);b.cancel();b.close();b.close()
        self.assertTrue(w.cancelled);self.assertTrue(w.closed)
        with self.assertRaises(RuntimeError):b.start()
if __name__=='__main__':unittest.main()
