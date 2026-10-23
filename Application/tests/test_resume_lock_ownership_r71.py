"""R71: lock ownership is a publication precondition (fake SFTP, not live).
Author: Abdelhalim Talbi.
"""
import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from transfer_safety import download_resume_verified


class SFTP:
    def __init__(self, on_open=None):
        self.on_open = on_open

    def stat(self, path):
        return SimpleNamespace(st_size=6, st_mtime=123, st_mode=0o100600)

    def open(self, path, mode):
        if self.on_open:
            self.on_open()
        return io.BytesIO(b'123456')


class LockOwnershipR71(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.target = self.root / 'target.bin'
        token = hashlib.sha256(('conn\0/remote\0' + str(self.target.resolve())).encode()).hexdigest()[:20]
        self.lock = self.root / ('.openremote-' + token + '.lock')
        self.partial = self.root / ('.openremote-' + token + '.part')

    def resume(self, on_open=None):
        return download_resume_verified(SFTP(on_open), '/remote', self.target, 'conn', chunk_size=2)

    def test_success_publishes_and_releases_owned_lock(self):
        self.assertEqual(self.resume(), 6)
        self.assertEqual(self.target.read_bytes(), b'123456')
        self.assertFalse(self.lock.exists())

    def test_replaced_lock_blocks_publication_and_preserves_new_owner(self):
        def replace():
            self.lock.unlink()
            self.lock.write_text('new owner')
        with self.assertRaisesRegex(RuntimeError, 'Verrou'):
            self.resume(replace)
        self.assertFalse(self.target.exists())
        self.assertTrue(self.partial.exists())
        self.assertEqual(self.lock.read_text(), 'new owner')

    def test_same_inode_marker_tamper_blocks_publication(self):
        def tamper():
            with self.lock.open('r+b') as stream:
                stream.seek(0)
                stream.write(b'X' * 32)
        with self.assertRaisesRegex(RuntimeError, 'Verrou'):
            self.resume(tamper)
        self.assertFalse(self.target.exists())
        self.assertTrue(self.partial.exists())

    def test_removed_lock_blocks_publication(self):
        with self.assertRaisesRegex(RuntimeError, 'Verrou'):
            self.resume(lambda: self.lock.unlink())
        self.assertFalse(self.target.exists())
        self.assertTrue(self.partial.exists())
        self.assertFalse(self.lock.exists())

    @unittest.skipIf(os.name == 'nt', 'Symlink creation may require Windows developer mode')
    def test_symlink_lock_blocks_publication_without_touching_target(self):
        victim = self.root / 'victim.txt'
        victim.write_text('untouched')
        def replace():
            self.lock.unlink()
            self.lock.symlink_to(victim)
        with self.assertRaisesRegex(RuntimeError, 'Verrou'):
            self.resume(replace)
        self.assertFalse(self.target.exists())
        self.assertTrue(self.lock.is_symlink())
        self.assertEqual(victim.read_text(), 'untouched')

    def test_lock_marker_corrupted_during_cleanup_is_preserved(self):
        """A changed lock must not be deleted by the transfer cleanup."""
        def corrupt():
            with self.lock.open('r+b') as stream:
                stream.seek(0)
                stream.write(b'Z' * 32)
        with self.assertRaisesRegex(RuntimeError, 'Verrou'):
            self.resume(corrupt)
        self.assertTrue(self.lock.exists())
        self.assertEqual(self.lock.read_bytes(), b'Z' * 32)
        self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
