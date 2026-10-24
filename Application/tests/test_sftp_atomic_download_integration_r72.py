"""End-to-end local filesystem qualification of atomic SFTP downloads.

Uses a deterministic fake SFTP transport; no real server is claimed.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from transfer_safety import download_atomic


class FakeSftp:
    def __init__(self, payload, fail=False):
        self.payload=payload
        self.fail=fail

    def stat(self, remote):
        from types import SimpleNamespace
        return SimpleNamespace(st_size=len(self.payload))

    def get(self, remote, local, callback=None):
        assert remote == './report.bin'
        with open(local, 'wb') as output:
            output.write(self.payload)
        if callback:
            callback(len(self.payload),len(self.payload))
        if self.fail:
            raise OSError('simulated transport interruption')


class AtomicDownloadIntegrationTests(unittest.TestCase):
    def test_success_replaces_target(self):
        with TemporaryDirectory() as directory:
            target=Path(directory)/'report.bin'
            target.write_bytes(b'previous')
            download_atomic(FakeSftp(b'new payload'),'./report.bin',target)
            self.assertEqual(target.read_bytes(),b'new payload')
            self.assertEqual(list(Path(directory).glob('*.part')),[])

    def test_short_download_is_never_published(self):
        class TruncatedSftp(FakeSftp):
            def stat(self, remote):
                from types import SimpleNamespace
                return SimpleNamespace(st_size=len(self.payload)+10)
        with TemporaryDirectory() as directory:
            target=Path(directory)/'report.bin'
            target.write_bytes(b'previous')
            with self.assertRaises(OSError):
                download_atomic(TruncatedSftp(b'short'),'./report.bin',target)
            self.assertEqual(target.read_bytes(),b'previous')
            self.assertEqual(list(Path(directory).glob('*.part')),[])

    def test_remote_file_changes_during_transfer(self):
        class ChangingSftp(FakeSftp):
            def __init__(self, payload):
                super().__init__(payload)
                self.calls=0
            def stat(self, remote):
                from types import SimpleNamespace
                self.calls+=1
                return SimpleNamespace(st_size=len(self.payload), st_mtime=self.calls, st_mode=0o100644)
        with TemporaryDirectory() as directory:
            target=Path(directory)/'report.bin'
            target.write_bytes(b'previous')
            with self.assertRaises(OSError):
                download_atomic(ChangingSftp(b'new'),'./report.bin',target)
            self.assertEqual(target.read_bytes(),b'previous')
            self.assertEqual(list(Path(directory).glob('*.part')),[])

    def test_transport_failure_preserves_target(self):
        with TemporaryDirectory() as directory:
            target=Path(directory)/'report.bin'
            target.write_bytes(b'previous')
            with self.assertRaises(OSError):
                download_atomic(FakeSftp(b'incomplete',fail=True),'./report.bin',target)
            self.assertEqual(target.read_bytes(),b'previous')
            self.assertEqual(list(Path(directory).glob('*.part')),[])

    def test_cancel_during_progress_preserves_target(self):
        with TemporaryDirectory() as directory:
            target=Path(directory)/'report.bin'
            target.write_bytes(b'previous')
            stop=[False]
            def on_progress(done,total):
                stop[0]=True
            with self.assertRaises(InterruptedError):
                download_atomic(FakeSftp(b'incomplete'),'./report.bin',target,
                                callback=on_progress,cancelled=lambda: stop[0])
            self.assertEqual(target.read_bytes(),b'previous')
            self.assertEqual(list(Path(directory).glob('*.part')),[])

    def test_cancel_before_publication_preserves_target(self):
        with TemporaryDirectory() as directory:
            target=Path(directory)/'report.bin'
            target.write_bytes(b'previous')
            with self.assertRaises(InterruptedError):
                download_atomic(FakeSftp(b'new'),'./report.bin',target,
                                cancelled=lambda: True)
            self.assertEqual(target.read_bytes(),b'previous')


if __name__ == '__main__':
    unittest.main()
