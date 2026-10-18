import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class BridgeStaticContract(unittest.TestCase):
    def test_bridge_is_syntactically_valid(self):
        ast.parse((ROOT / 'ssh_qt_bridge.py').read_text(encoding='utf-8'))
    def test_owner_thread_guard_on_public_methods(self):
        tree = ast.parse((ROOT / 'ssh_qt_bridge.py').read_text(encoding='utf-8'))
        cls = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'SSHQtBridge')
        methods = {x.name: x for x in cls.body if isinstance(x, ast.FunctionDef)}
        for name in ('start', 'cancel', 'close', '_deliver_success', '_deliver_error'):
            self.assertIn('_require_owner_thread()', ast.unparse(methods[name]))
    def test_signal_delivery_is_queued(self):
        code=(ROOT / 'ssh_qt_bridge.py').read_text(encoding='utf-8')
        self.assertEqual(code.count('Qt.ConnectionType.QueuedConnection'), 2)

try:
    from PySide6.QtCore import QCoreApplication, QThread
    from ssh_qt_bridge import SSHQtBridge
except ImportError:
    SSHQtBridge=None

class FakeWorker:
    def connect(self,on_success,on_error):
        self.success=on_success;self.error=on_error
    def cancel(self): pass
    def close(self): pass

@unittest.skipIf(SSHQtBridge is None, 'PySide6 unavailable; native Qt test required')
class BridgeRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QCoreApplication.instance() or QCoreApplication([])
    def test_owner_thread_delivery(self):
        w=FakeWorker();b=SSHQtBridge(w);seen=[]
        b.connected.connect(lambda resource: seen.append(QThread.currentThread()==b.thread()))
        b.start();w.success(object());self.app.processEvents()
        self.assertEqual(seen,[True]);b.close()
