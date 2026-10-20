"""Atomic SFTP download publication tests. Author: Abdelhalim Talbi."""
import tempfile
import unittest
from pathlib import Path
from transfer_safety import download_atomic


class FakeSFTP:
    def __init__(self, data=b"payload", before_return=None, failure=None):
        self.data = data
        self.before_return = before_return
        self.failure = failure

    def get(self, remote_path, local_path, callback=None):
        with open(local_path, "wb") as stream:
            stream.write(self.data)
        if callback:
            callback(len(self.data), len(self.data))
        if self.before_return:
            self.before_return()
        if self.failure:
            raise self.failure


class AtomicDownloadTests(unittest.TestCase):
    def test_success_replaces_file_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "result"
            target.write_bytes(b"original")
            download_atomic(FakeSFTP(), "/remote", target)
            self.assertEqual(target.read_bytes(), b"payload")
            self.assertEqual(list(Path(folder).glob(".openremote-*.part")), [])

    def test_network_error_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "result"
            target.write_bytes(b"original")
            with self.assertRaises(OSError):
                download_atomic(FakeSFTP(failure=OSError("network")), "/remote", target)
            self.assertEqual(target.read_bytes(), b"original")
            self.assertEqual(list(Path(folder).glob(".openremote-*.part")), [])

    def test_cancel_before_publication_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "result"
            target.write_bytes(b"original")
            state = {"cancel": False}
            def progress(done, total):
                state["cancel"] = True
            with self.assertRaises(InterruptedError):
                download_atomic(FakeSFTP(), "/remote", target, callback=progress,
                                cancelled=lambda: state["cancel"])
            self.assertEqual(target.read_bytes(), b"original")
            self.assertEqual(list(Path(folder).glob(".openremote-*.part")), [])

    def test_symlink_before_transfer_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / "original"
            original.write_bytes(b"keep")
            target = root / "result"
            try:
                target.symlink_to(original)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable")
            with self.assertRaisesRegex(ValueError, "symbolique"):
                download_atomic(FakeSFTP(), "/remote", target)
            self.assertEqual(original.read_bytes(), b"keep")

    def test_symlink_created_during_transfer_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / "original"
            original.write_bytes(b"keep")
            target = root / "result"
            def create_link():
                try:
                    target.symlink_to(original)
                except (OSError, NotImplementedError):
                    self.skipTest("Symlinks unavailable")
            with self.assertRaisesRegex(ValueError, "symbolique"):
                download_atomic(FakeSFTP(before_return=create_link), "/remote", target)
            self.assertEqual(original.read_bytes(), b"keep")
            self.assertEqual(list(root.glob(".openremote-*.part")), [])


if __name__ == "__main__":
    unittest.main()
