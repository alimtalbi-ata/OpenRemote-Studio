import ast, pathlib, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
class BridgeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'ssh_qt_bridge.py').read_text(encoding='utf-8')
        cls.tree=ast.parse(cls.source)
    def test_queued_connection_explicit(self):
        self.assertIn('Qt.ConnectionType.QueuedConnection', self.source)
    def test_generation_checked_at_delivery(self):
        self.assertIn('self._gate.deliver(generation, resource',self.source)
    def test_close_invalidates_gate(self):
        self.assertIn('self._gate.close()',self.source)
    def test_duplicate_start_precheck(self):
        self.assertIn("getattr(self.worker, 'is_connecting', False)",self.source)
    def test_callbacks_do_not_touch_widgets(self):
        self.assertNotIn('QWidget',self.source.replace('No QWidget is touched here.',''))
if __name__=='__main__':unittest.main()
