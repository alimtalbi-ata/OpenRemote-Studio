"""Regression tests for cooperative SFTP upload cancellation. Author: Abdelhalim Talbi."""
import tempfile
import unittest
from pathlib import Path
from transfer_safety import upload_exclusive


class Remote:
    def __init__(self, owner):
        self.owner = owner
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def write(self, chunk):
        self.owner.data += chunk


class FakeSFTP:
    def __init__(self, exists=False):
        self.exists = exists
        self.data = b""
        self.removed = []
    def open(self, path, mode):
        assert mode == "wbx"
        if self.exists:
            raise FileExistsError(path)
        self.exists = True
        return Remote(self)
    def remove(self, path):
        self.removed.append(path)
        self.exists = False


class CancellationTests(unittest.TestCase):
    def test_cancel_before_create_preserves_remote(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"
            source.write_bytes(b"abcd")
            remote = FakeSFTP()
            with self.assertRaises(InterruptedError):
                upload_exclusive(remote, source, "/target", cancelled=lambda: True)
            self.assertFalse(remote.exists)
            self.assertEqual(remote.removed, [])

    def test_cancel_after_first_chunk_removes_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"
            source.write_bytes(b"abcdef")
            remote = FakeSFTP()
            state = {"cancel": False}
            def progress(done, total):
                state["cancel"] = done >= 2
            with self.assertRaises(InterruptedError):
                upload_exclusive(remote, source, "/target", callback=progress,
                                 chunk_size=2, cancelled=lambda: state["cancel"])
            self.assertEqual(remote.data, b"ab")
            self.assertEqual(remote.removed, ["/target"])

    def test_existing_remote_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"
            source.write_bytes(b"abcdef")
            remote = FakeSFTP(exists=True)
            with self.assertRaises(FileExistsError):
                upload_exclusive(remote, source, "/target", cancelled=lambda: False)
            self.assertEqual(remote.removed, [])


if __name__ == "__main__":
    unittest.main()
