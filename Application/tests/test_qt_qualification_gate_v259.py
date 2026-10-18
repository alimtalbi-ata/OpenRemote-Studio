import importlib.util
import pathlib
import unittest
from unittest.mock import patch

FILE = pathlib.Path(__file__).resolve().parents[2] / '02-Compilation' / 'qualify_qt.py'
spec = importlib.util.spec_from_file_location('qualify_qt', FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class QualificationGateTests(unittest.TestCase):
    def test_missing_pyside6_is_blocking(self):
        import builtins
        original = builtins.__import__
        def reject(name, *args, **kwargs):
            if name == 'PySide6':
                raise ImportError('simulated missing dependency')
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=reject):
            self.assertEqual(module.main(), 3)
    def test_qualification_script_present(self):
        self.assertTrue(FILE.is_file())
        self.assertIn('result.skipped', FILE.read_text())
