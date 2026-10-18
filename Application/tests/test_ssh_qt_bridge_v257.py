import os, unittest
from concurrent.futures import Future
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtCore import QCoreApplication
    from ssh_qt_bridge import SSHQtBridge
except ImportError:
    SSHQtBridge = None

class Worker:
    def connect(self,on_success,on_error):
        self.success=on_success; self.failure=on_error
        f=Future(); f.set_result(None); return f
    def cancel(self): return None
    def close(self): return None
class Resource:
    def __init__(self): self.closed=0
    def close(self): self.closed+=1

@unittest.skipIf(SSHQtBridge is None,'PySide6 unavailable')
class BridgeDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QCoreApplication.instance() or QCoreApplication([])
    def test_cancel_after_emit_before_qt_delivery(self):
        w=Worker(); b=SSHQtBridge(w); got=[]; b.connected.connect(got.append)
        b.start(); r=Resource(); w.success(r); b.cancel(); self.app.processEvents()
        self.assertEqual(got,[]); self.assertEqual(r.closed,1); b.close()
    def test_current_delivery(self):
        w=Worker(); b=SSHQtBridge(w); got=[]; b.connected.connect(got.append)
        b.start(); r=Resource(); w.success(r); self.app.processEvents()
        self.assertEqual(got,[r]); self.assertEqual(r.closed,0); b.close()
    def test_close_before_queued_error(self):
        w=Worker(); b=SSHQtBridge(w); got=[]; b.failed.connect(got.append)
        b.start(); w.failure(OSError('network')); b.close(); self.app.processEvents()
        self.assertEqual(got,[])
