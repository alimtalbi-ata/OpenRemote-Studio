"""Static safety contracts for the actual Tk SSH tab integration."""
import ast, pathlib, unittest
SRC=pathlib.Path(__file__).resolve().parents[1]/'app.py'
class TkIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SRC.read_text();cls.tree=ast.parse(cls.source)
    def test_bridge_instantiated_inside_real_ssh_tab(self):
        fn=next(n for n in ast.walk(self.tree) if isinstance(n,ast.FunctionDef) and n.name=='ssh_tab')
        self.assertIn('TkSSHEventBridge(',ast.get_source_segment(self.source,fn))
    def test_poll_drains_bridge_on_tk_owner(self):
        fn=next(n for n in ast.walk(self.tree) if isinstance(n,ast.FunctionDef) and n.name=='poll')
        self.assertIn("session['bridge'].drain",ast.get_source_segment(self.source,fn))
    def test_session_tab_closure_invalidates_bridge(self):
        self.assertIn('bridge.close()',self.source)
        self.assertIn("s['close']()",self.source)
