"""Security regression cases for the portable archive release gate."""
import importlib.util
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'windows' / 'verify-binary-artifacts.py'
spec = importlib.util.spec_from_file_location('verify_binary_artifacts_v305', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PortableSecurityTests(unittest.TestCase):
    def check(self, filename, content=b'abc', mode=None):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'bad.zip'
            with zipfile.ZipFile(path, 'w') as z:
                info = zipfile.ZipInfo(filename)
                if mode is not None:
                    info.create_system = 3
                    info.external_attr = (mode << 16)
                z.writestr(info, content)
            return mod.verify_portable(path, onefile=True)

    def test_symlink_rejected(self):
        self.assertTrue(any('Symlink' in s for s in self.check('link', b'../../etc', stat.S_IFLNK | 0o777)))

    def test_windows_trailing_dot_rejected(self):
        self.assertTrue(any('Unsafe path' in s for s in self.check('folder./evil.txt')))

    def test_windows_trailing_space_rejected(self):
        self.assertTrue(any('Unsafe path' in s for s in self.check('folder /evil.txt')))

    def test_traversal_rejected(self):
        self.assertTrue(any('Unsafe path' in s for s in self.check('../evil.exe')))

    def test_case_collision_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'bad.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('ABC.txt', b'a')
                z.writestr('abc.txt', b'b')
            self.assertTrue(any('colliding' in s for s in mod.verify_portable(path, onefile=True)))
