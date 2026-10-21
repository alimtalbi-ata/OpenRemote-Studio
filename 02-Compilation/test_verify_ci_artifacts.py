"""Regression tests for Windows artifact publication gates.

Run with: python -m unittest discover -s 02-Compilation -p 'test_verify_ci_artifacts.py'
Author: Abdelhalim Talbi.
"""
import importlib.util
import pathlib
import tempfile
import unittest
import zipfile

SCRIPT = pathlib.Path(__file__).with_name("verify_ci_artifacts.py")
spec = importlib.util.spec_from_file_location("verify_ci_artifacts", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArtifactGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / "VERSION.txt").write_text("31.4\n", encoding="utf-8")
        self.folder = self.root / "Binary" / "V31.4"
        self.installer = self.folder / "Installer" / "OpenRemoteStudio-V31.4-Windows-Setup.exe"
        self.portable = self.folder / "Portable" / "OpenRemoteStudio-V31.4-Windows-Portable.zip"
        self.installer.parent.mkdir(parents=True)
        self.portable.parent.mkdir(parents=True)
        self.installer.write_bytes(b"MZ" + b"0" * 2048)
        with zipfile.ZipFile(self.portable, "w") as archive:
            archive.writestr("OpenRemoteStudio.exe", b"MZ" + b"1" * 2048)

    def test_valid_candidate(self):
        self.assertEqual(len(module.verify(self.root)), 2)

    def test_rejects_fake_installer(self):
        self.installer.write_bytes(b"XX" + b"0" * 2048)
        with self.assertRaisesRegex(ValueError, "not a Windows PE"):
            module.verify(self.root)

    def test_rejects_missing_executable(self):
        with zipfile.ZipFile(self.portable, "w") as archive:
            archive.writestr("README.txt", "placeholder" * 256)
        with self.assertRaisesRegex(ValueError, "does not contain"):
            module.verify(self.root)

    def test_rejects_zip_traversal(self):
        with zipfile.ZipFile(self.portable, "w") as archive:
            archive.writestr("../OpenRemoteStudio.exe", b"MZ" + b"1" * 2048)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            module.verify(self.root)

    def test_rejects_missing_installer(self):
        self.installer.unlink()
        with self.assertRaisesRegex(ValueError, "Missing or empty"):
            module.verify(self.root)


if __name__ == "__main__":
    unittest.main()
