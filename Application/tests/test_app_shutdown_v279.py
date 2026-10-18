import ast
import unittest
from pathlib import Path

class ShutdownContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / 'app.py').read_text()
        cls.tree = ast.parse(cls.source)

    def test_sftp_shutdown_off_ui_thread(self):
        self.assertIn('scope=NetworkResourceScope()', self.source)
        self.assertIn('scope.close()', self.source)

    def test_tunnel_shutdown_off_ui_thread(self):
        self.assertIn('for scope in self.network_scopes:', self.source)
        self.assertIn('scope.close()', self.source)

    def test_cleanup_is_exception_isolated(self):
        from network_resource_scope import close_quietly
        class Broken:
            def close(self): raise OSError('closed')
        self.assertIsNone(close_quietly(Broken()))
