"""Qt event-loop integration tests, executed only when PySide6 is available."""
import threading
import unittest
try:
    from PySide6.QtCore import QCoreApplication, QTimer
    from ssh_qt_bridge import SSHQtBridge
except ImportError:
    SSHQtBridge = None


@unittest.skipIf(SSHQtBridge is None, 'PySide6 unavailable: Qt integration unqualified')
class QtEventLoopIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def drain(self):
        for _ in range(20):
            self.app.processEvents()

    def test_background_success_delivered_on_owner_thread(self):
        owner = threading.get_ident()
        class Worker:
            def connect(self, on_success, on_error):
                t = threading.Thread(target=lambda: on_success('connected'))
                t.start(); t.join()
            def close(self): pass
        bridge = SSHQtBridge(Worker())
        seen = []
        bridge.connected.connect(lambda value: seen.append((value, threading.get_ident())))
        bridge.start(); self.drain()
        self.assertEqual(seen, [('connected', owner)])
        bridge.close()

    def test_cancel_before_queued_delivery_closes_stale_resource(self):
        class Resource:
            def __init__(self): self.closed = False
            def close(self): self.closed = True
        resource = Resource()
        class Worker:
            def connect(self, on_success, on_error):
                t = threading.Thread(target=lambda: on_success(resource))
                t.start(); t.join()
            def cancel(self): pass
            def close(self): pass
        bridge = SSHQtBridge(Worker()); seen = []
        bridge.connected.connect(seen.append)
        bridge.start(); bridge.cancel(); self.drain()
        self.assertEqual(seen, [])
        self.assertTrue(resource.closed)
        bridge.close()

    def test_background_error_delivered_on_owner_thread(self):
        owner = threading.get_ident()
        class Worker:
            def connect(self, on_success, on_error):
                t = threading.Thread(target=lambda: on_error(ValueError('simulated failure')))
                t.start(); t.join()
            def close(self): pass
        bridge = SSHQtBridge(Worker()); seen = []
        bridge.failed.connect(lambda message: seen.append((message, threading.get_ident())))
        bridge.start(); self.drain()
        self.assertEqual(len(seen), 1)
        self.assertIn('simulated failure', seen[0][0]); self.assertEqual(seen[0][1], owner)
        bridge.close()
