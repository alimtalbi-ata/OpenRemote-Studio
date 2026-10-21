"""Resumed SFTP download cancellation regression. Author: Abdelhalim Talbi."""
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from transfer_safety import download_resume_verified


class Remote(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class SFTP:
    def __init__(self, data, mtime=100, mode=0o100644):
        self.data = data
        self.mtime = mtime
        self.mode = mode
        self.stat_calls = 0
    def stat(self, path):
        self.stat_calls += 1
        return SimpleNamespace(st_size=len(self.data), st_mtime=self.mtime, st_mode=self.mode)
    def open(self, path, mode):
        if mode != "rb":
            raise AssertionError(mode)
        return Remote(self.data)


def partial_path(identity, remote, target):
    token = hashlib.sha256((identity + "\0" + remote + "\0" +
                            str(target.resolve())).encode()).hexdigest()[:20]
    return target.parent / (".openremote-" + token + ".part")


class ResumeCancellationTests(unittest.TestCase):
    def test_cancel_before_download_does_not_create_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "result"
            with self.assertRaises(InterruptedError):
                download_resume_verified(SFTP(b"abcdef"), "/remote", target,
                                         "connection", cancelled=lambda: True)
            self.assertFalse(target.exists())
            self.assertFalse(partial_path("connection", "/remote", target).exists())

    def test_cancel_during_download_keeps_partial_and_original(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "result"
            target.write_bytes(b"old")
            state = {"stop": False}
            def progress(done, total):
                state["stop"] = done >= 2
            with self.assertRaises(InterruptedError):
                download_resume_verified(SFTP(b"abcdef"), "/remote", target,
                                         "connection", callback=progress, chunk_size=2,
                                         cancelled=lambda: state["stop"])
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(partial_path("connection", "/remote", target).read_bytes(), b"ab")

    def test_remote_mtime_change_blocks_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            target.write_bytes(b'old')
            sftp = SFTP(b'abcdef')
            def progress(done, total):
                if done >= 2:
                    sftp.mtime = 101
            with self.assertRaisesRegex(ValueError, 'Horodatage'):
                download_resume_verified(sftp, '/remote', target, 'connection',
                                         callback=progress, chunk_size=2)
            self.assertEqual(target.read_bytes(), b'old')
            self.assertEqual(partial_path('connection', '/remote', target).read_bytes(), b'abcdef')

    def test_symlink_partial_is_rejected_without_modifying_victim(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            victim = root / 'victim'
            victim.write_bytes(b'keep')
            target = root / 'result'
            partial = partial_path('connection', '/remote', target)
            try:
                partial.symlink_to(victim)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable on this Windows runner')
            with self.assertRaisesRegex(ValueError, 'partiel symbolique'):
                download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                         'connection', chunk_size=2)
            self.assertEqual(victim.read_bytes(), b'keep')
            self.assertFalse(target.exists())

    def test_symlink_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / 'original'
            original.write_bytes(b'keep')
            target = root / 'result'
            try:
                target.symlink_to(original)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable on this Windows runner')
            with self.assertRaisesRegex(ValueError, 'symbolique'):
                download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                         'connection')
            self.assertEqual(original.read_bytes(), b'keep')

    def test_remote_mode_change_blocks_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            target.write_bytes(b'original')
            sftp = SFTP(b'abcdef')
            def progress(done, total):
                if done >= 2:
                    sftp.mode = 0o100600
            with self.assertRaisesRegex(ValueError, 'permissions'):
                download_resume_verified(sftp, '/remote', target, 'connection',
                                         callback=progress, chunk_size=2)
            self.assertEqual(target.read_bytes(), b'original')

    def test_empty_remote_path_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'Chemin distant'):
                download_resume_verified(SFTP(b'abcdef'), '', Path(folder) / 'result',
                                         'connection')

    def test_remote_size_change_blocks_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            target.write_bytes(b'original')
            sftp = SFTP(b'abcdef')
            def progress(done, total):
                if done >= 2:
                    sftp.data = b'abcdefg'
            with self.assertRaisesRegex(ValueError, 'modifié'):
                download_resume_verified(sftp, '/remote', target, 'connection',
                                         callback=progress, chunk_size=2)
            self.assertEqual(target.read_bytes(), b'original')
            self.assertTrue(partial_path('connection', '/remote', target).exists())

    def test_changed_remote_prefix_rejects_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            target.write_bytes(b'original')
            partial_path('connection', '/remote', target).write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'reprise refusée'):
                download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                         'connection', chunk_size=2)
            self.assertEqual(target.read_bytes(), b'original')
            self.assertEqual(partial_path('connection', '/remote', target).read_bytes(), b'bad')

    def test_directory_partial_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            partial = partial_path('connection', '/remote', target)
            partial.mkdir()
            with self.assertRaisesRegex(ValueError, 'non régulier'):
                download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                         'connection', chunk_size=2)
            self.assertTrue(partial.is_dir())
            self.assertFalse(target.exists())

    def test_target_symlink_created_during_resume_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'result'
            victim = root / 'victim'
            victim.write_bytes(b'untouched')
            def progress(done, total):
                if done >= total and not target.exists() and not target.is_symlink():
                    try:
                        target.symlink_to(victim)
                    except (OSError, NotImplementedError):
                        self.skipTest('Symlinks unavailable')
            with self.assertRaisesRegex(ValueError, 'symbolique'):
                download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                         'connection', callback=progress, chunk_size=2)
            self.assertEqual(victim.read_bytes(), b'untouched')
            parts = list(root.glob('.openremote-*.part'))
            self.assertEqual(len(parts), 1)
            self.assertEqual(parts[0].read_bytes(), b'abcdef')

    def test_cancelled_request_does_not_touch_residual_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            lock = partial_path('connection', '/remote', target).with_suffix('.lock')
            lock.write_text('owner', encoding='utf-8')
            with self.assertRaises(InterruptedError):
                download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                         'connection', cancelled=lambda: True)
            self.assertEqual(lock.read_text(encoding='utf-8'), 'owner')
            self.assertFalse(target.exists())

    def test_residual_lock_is_not_deleted_or_overridden(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            lock = partial_path('connection', '/remote', target).with_suffix('.lock')
            lock.write_text('existing owner', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'verrou résiduel'):
                download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                         'connection', chunk_size=2)
            self.assertEqual(lock.read_text(encoding='utf-8'), 'existing owner')
            self.assertFalse(target.exists())

    def test_lock_is_removed_on_transfer_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            lock = partial_path('connection', '/remote', target).with_suffix('.lock')
            with self.assertRaisesRegex(OSError, 'network failure'):
                class FailingSFTP(SFTP):
                    def open(self, path, mode):
                        raise OSError('network failure')
                download_resume_verified(FailingSFTP(b'abcdef'), '/remote', target,
                                         'connection', chunk_size=2)
            self.assertFalse(lock.exists())

    def test_concurrent_resume_is_rejected_and_lock_released(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            attempted = []
            def progress(done, total):
                if not attempted:
                    with self.assertRaisesRegex(RuntimeError, 'Reprise déjà en cours'):
                        download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                                 'connection', chunk_size=2)
                    attempted.append(True)
            self.assertEqual(download_resume_verified(SFTP(b'abcdef'), '/remote', target,
                                                      'connection', callback=progress,
                                                      chunk_size=2), 6)
            self.assertEqual(attempted, [True])
            self.assertEqual(list(Path(folder).glob('.openremote-*.lock')), [])

    def test_metadata_uses_two_consistent_snapshots(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result'
            sftp = SFTP(b'abcdef')
            self.assertEqual(download_resume_verified(sftp, '/remote', target,
                                                      'connection', chunk_size=2), 6)
            self.assertEqual(sftp.stat_calls, 2)
            self.assertEqual(target.read_bytes(), b'abcdef')

    def test_successful_resume_publishes_complete_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "result"
            partial_path("connection", "/remote", target).write_bytes(b"ab")
            result = download_resume_verified(SFTP(b"abcdef"), "/remote", target,
                                              "connection", chunk_size=2,
                                              cancelled=lambda: False)
            self.assertEqual(result, 6)
            self.assertEqual(target.read_bytes(), b"abcdef")
            self.assertFalse(partial_path("connection", "/remote", target).exists())


if __name__ == "__main__":
    unittest.main()
