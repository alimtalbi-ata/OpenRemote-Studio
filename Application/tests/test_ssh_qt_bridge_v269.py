"""Qt integration tests: skipped, not counted as passed, without PySide6."""
import unittest
try:
    from PySide6.QtCore import QCoreApplication
    from ssh_qt_bridge import SSHQtBridge
except ImportError:
    SSHQtBridge = None

@unittest.skipIf(SSHQtBridge is None, "PySide6 unavailable")
class StartFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_sync_failure_invalidates_queued_success_and_closes_resource(self):
        class Resource:
            closed = False
            def close(self): self.closed = True
        resource = Resource()
        class Worker:
            def connect(self, on_success, on_error):
                on_success(resource)
                raise ValueError('startup failed')
            def close(self): pass
        bridge = SSHQtBridge(Worker()); delivered=[]
        bridge.connected.connect(delivered.append)
        with self.assertRaisesRegex(ValueError, 'startup failed'): bridge.start()
        self.app.processEvents()
        self.assertTrue(resource.closed)
        self.assertEqual(delivered, [])
        bridge.close()

    def test_retry_after_synchronous_failure(self):
        class Worker:
            attempts = 0
            def connect(self, on_success, on_error):
                self.attempts += 1
                if self.attempts == 1: raise RuntimeError('temporary')
                on_success('ok')
            def close(self): pass
        bridge = SSHQtBridge(Worker()); seen=[]
        bridge.connected.connect(seen.append)
        with self.assertRaises(RuntimeError): bridge.start()
        bridge.start(); self.app.processEvents()
        self.assertEqual(seen,['ok']); bridge.close()
