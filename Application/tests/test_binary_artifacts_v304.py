"""Executable/portable release gate tests, independent of Windows host."""
import importlib.util
import io
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'windows' / 'verify-binary-artifacts.py'
spec = importlib.util.spec_from_file_location('verify_binary_artifacts', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def pe():
    data = bytearray(600)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<H', data, 148, 224)
    return bytes(data)


class BinaryArtifactsTests(unittest.TestCase):
    def test_pe_rejects_fake_and_truncated(self):
        self.assertTrue(mod.valid_pe(pe()))
        self.assertFalse(mod.valid_pe(b'MZ' + bytes(510)))
        self.assertFalse(mod.valid_pe(b'PE' + bytes(510)))

    def test_portable_onedir_requires_runtime_and_plugin(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / 'portable.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('OpenRemoteStudio/OpenRemoteStudio.exe', pe())
            self.assertTrue(mod.verify_portable(archive))
            self.assertEqual(mod.verify_portable(archive, onefile=True), [])
            with zipfile.ZipFile(archive, 'a') as z:
                z.writestr('OpenRemoteStudio/_internal/PySide6/Qt/plugins/platforms/qwindows.dll', b'qt')
                z.writestr('OpenRemoteStudio/_internal/python311.dll', b'python')
            self.assertEqual(mod.verify_portable(archive), [])

    def test_portable_rejects_fake_exe(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / 'portable.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('OpenRemoteStudio.exe', b'fake binary')
            self.assertTrue(mod.verify_portable(archive, onefile=True))

    def test_installer_rejects_non_pe(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'setup.exe'
            file.write_bytes(b'not a windows executable')
            self.assertTrue(mod.verify_installer(file))
            file.write_bytes(pe())
            self.assertEqual(mod.verify_installer(file), [])

    def test_build_invokes_gate_before_publication(self):
        script = (SCRIPT.parent / 'build-windows.ps1').read_text(encoding='utf-8')
        self.assertLess(script.index('verify-binary-artifacts.py'), script.index('Move-Item -LiteralPath $release'))
        self.assertIn("throw 'Binary artifact validation failed'", script)

if __name__ == '__main__':
    unittest.main()
