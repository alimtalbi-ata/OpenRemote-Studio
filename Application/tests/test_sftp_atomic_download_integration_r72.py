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
    def test_upload_directory_and_missing_source_rejected(self):
        from transfer_safety import upload_exclusive
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                upload_exclusive(None, directory, './report.bin')
            with self.assertRaises(ValueError):
                upload_exclusive(None, str(Path(directory)/'missing.bin'), './report.bin')

    def test_upload_symlink_source_rejected(self):
        from transfer_safety import upload_exclusive
        with TemporaryDirectory() as directory:
            source=Path(directory)/'source.bin'
            source.write_bytes(b'data')
            link=Path(directory)/'link.bin'
            try:
                link.symlink_to(source)
            except (OSError,NotImplementedError):
                self.skipTest('Symlinks unavailable')
            with self.assertRaises(ValueError):
                upload_exclusive(None, str(link), './report.bin')

    def test_upload_short_writes_complete(self):
        from transfer_safety import upload_exclusive
        class Remote:
            def __init__(self):
                self.payload=bytearray()
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def write(self,data):
                count=min(2,len(data))
                self.payload.extend(data[:count])
                return count
        class Sftp:
            def __init__(self):self.remote=Remote()
            def open(self,path,mode):
                assert mode=='wbx'
                return self.remote
        with TemporaryDirectory() as directory:
            source=Path(directory)/'source.bin'
            source.write_bytes(b'1234567')
            sftp=Sftp()
            self.assertEqual(upload_exclusive(sftp,source,'./source.bin',chunk_size=4),7)
            self.assertEqual(bytes(sftp.remote.payload),b'1234567')

    def test_upload_same_size_source_mutation_rejected(self):
        from transfer_safety import upload_exclusive
        import os
        class Remote:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def write(self,data):return len(data)
        class Sftp:
            def __init__(self):self.removed=[]
            def open(self,path,mode):return Remote()
            def remove(self,path):self.removed.append(path)
        with TemporaryDirectory() as directory:
            source=Path(directory)/'source.bin'
            source.write_bytes(b'12345678')
            sftp=Sftp()
            def mutate(done,total):
                if done==4:
                    before=source.stat()
                    source.write_bytes(b'abcdefgh')
                    os.utime(source,ns=(before.st_atime_ns,before.st_mtime_ns+2000000000))
            with self.assertRaises(OSError):
                upload_exclusive(sftp,source,'./source.bin',chunk_size=4,callback=mutate)
            self.assertEqual(sftp.removed,['./source.bin'])

    def test_upload_truncated_local_source_rejected(self):
        from transfer_safety import upload_exclusive
        class Remote:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def write(self,data):return len(data)
        class Sftp:
            def __init__(self):self.removed=[]
            def open(self,path,mode):return Remote()
            def remove(self,path):self.removed.append(path)
        with TemporaryDirectory() as directory:
            source=Path(directory)/'source.bin'
            source.write_bytes(b'12345678')
            sftp=Sftp()
            def truncate_after_first_chunk(done,total):
                if done==4:
                    source.write_bytes(b'1234')
            with self.assertRaises(OSError):
                upload_exclusive(sftp,source,'./source.bin',chunk_size=4,
                                 callback=truncate_after_first_chunk)
            self.assertEqual(sftp.removed,['./source.bin'])

    def test_upload_regular_file_success(self):
        from transfer_safety import upload_exclusive
        class Remote:
            def __init__(self):self.data=bytearray()
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def write(self,data):
                self.data.extend(data)
                return len(data)
        class Sftp:
            def __init__(self):self.remote=Remote()
            def open(self,path,mode):return self.remote
        with TemporaryDirectory() as directory:
            source=Path(directory)/'source.bin'
            source.write_bytes(b'normal')
            sftp=Sftp()
            self.assertEqual(upload_exclusive(sftp,source,'./source.bin'),6)
            self.assertEqual(bytes(sftp.remote.data),b'normal')

    def test_upload_buffered_write_returning_none(self):
        from transfer_safety import upload_exclusive
        class Remote:
            def __init__(self):self.data=bytearray()
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def write(self,data):
                self.data.extend(data)
                return None
        class Sftp:
            def __init__(self):self.remote=Remote()
            def open(self,path,mode):return self.remote
        with TemporaryDirectory() as directory:
            source=Path(directory)/'source.bin'
            source.write_bytes(b'buffered')
            sftp=Sftp()
            self.assertEqual(upload_exclusive(sftp,source,'./source.bin',chunk_size=3),8)
            self.assertEqual(bytes(sftp.remote.data),b'buffered')

    def test_upload_cancel_mid_write_cleans_remote(self):
        from transfer_safety import upload_exclusive
        class Remote:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def write(self,data):return 1
        class Sftp:
            def __init__(self):self.removed=[]
            def open(self,path,mode):return Remote()
            def remove(self,path):self.removed.append(path)
        with TemporaryDirectory() as directory:
            source=Path(directory)/'source.bin'
            source.write_bytes(b'abcd')
            progress=[]
            sftp=Sftp()
            with self.assertRaises(InterruptedError):
                upload_exclusive(sftp,source,'./source.bin',
                                 callback=lambda done,total:progress.append(done),
                                 cancelled=lambda:bool(progress))
            self.assertEqual(progress,[1])
            self.assertEqual(sftp.removed,['./source.bin'])

    def test_upload_zero_write_fails_and_cleans_remote(self):
        from transfer_safety import upload_exclusive
        class Remote:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def write(self,data):return 0
        class Sftp:
            def __init__(self):self.removed=[]
            def open(self,path,mode):return Remote()
            def remove(self,path):self.removed.append(path)
        with TemporaryDirectory() as directory:
            source=Path(directory)/'source.bin'
            source.write_bytes(b'data')
            sftp=Sftp()
            with self.assertRaises(OSError):
                upload_exclusive(sftp,source,'./source.bin')
            self.assertEqual(sftp.removed,['./source.bin'])

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
