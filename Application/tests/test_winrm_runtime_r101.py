"""R101: executable WinRM offline smoke contract and dynamic dependency probes.

Author: Abdelhalim Talbi.
"""
import builtins
import pathlib
import sys
import types
import unittest
from unittest.mock import patch
from winrm_runtime_check import runtime_dependency_available

APP = pathlib.Path(__file__).resolve().parents[1]

class RuntimeR101Tests(unittest.TestCase):
    def test_missing_winrm_dependency_fails_closed(self):
        original = builtins.__import__
        def no_winrm(name, *args, **kwargs):
            if name == 'winrm' or name.startswith('winrm.'):
                raise ImportError('offline synthetic missing dependency')
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=no_winrm):
            self.assertFalse(runtime_dependency_available())

    def test_complete_synthetic_graph_passes_without_network(self):
        winrm = types.ModuleType('winrm')
        winrm.__path__ = []
        winrm.Session = lambda *a, **kw: None
        protocol = types.ModuleType('winrm.protocol')
        protocol.Protocol = type('Protocol', (), {})
        ntlm = types.ModuleType('requests_ntlm')
        ntlm.HttpNtlmAuth = type('HttpNtlmAuth', (), {})
        spnego = types.ModuleType('spnego')
        spnego.client = lambda *a, **kw: None
        with patch.dict(sys.modules, {'winrm': winrm, 'winrm.protocol': protocol,
                                      'requests_ntlm': ntlm, 'spnego': spnego}):
            self.assertTrue(runtime_dependency_available())

    def test_partial_transport_fails_closed(self):
        winrm = types.ModuleType('winrm')
        winrm.__path__ = []
        winrm.Session = None
        protocol = types.ModuleType('winrm.protocol')
        protocol.Protocol = type('Protocol', (), {})
        ntlm = types.ModuleType('requests_ntlm')
        ntlm.HttpNtlmAuth = type('HttpNtlmAuth', (), {})
        spnego = types.ModuleType('spnego')
        spnego.client = lambda: None
        with patch.dict(sys.modules, {'winrm': winrm, 'winrm.protocol': protocol,
                                      'requests_ntlm': ntlm, 'spnego': spnego}):
            self.assertFalse(runtime_dependency_available())

    def test_packaging_specs_and_smokes_target_real_files(self):
        for name in ('OpenRemoteStudio.spec', 'OpenRemoteStudio-onefile.spec'):
            with self.subTest(spec=name):
                source = (APP / 'windows' / name).read_text(encoding='utf-8')
                self.assertIn("root.parent / 'qt_app.py'", source)
                self.assertIn("root.parent.parent / 'VERSION.txt'", source)
                self.assertIn('pathex=[str(root.parent)]', source)
                self.assertIn("collect_submodules('winrm')", source)
                self.assertIn("collect_submodules('spnego')", source)
                self.assertTrue((APP / 'qt_app.py').is_file())
        self.assertIn('pywinrm>=0.5,<0.6', (APP / 'requirements.txt').read_text())
        source = (APP / 'windows' / 'build-windows.ps1').read_text()
        self.assertEqual(source.count("'winrm-runtime-smoke.ps1'"), 2)
        self.assertIn('portableExecutables[0].FullName', source)
        self.assertIn("if '--check-winrm-runtime' in sys.argv:", (APP / 'qt_app.py').read_text())

if __name__ == '__main__':
    unittest.main()
