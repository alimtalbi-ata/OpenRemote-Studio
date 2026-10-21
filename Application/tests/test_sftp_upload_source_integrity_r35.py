"""R35 upload source identity/integrity regressions; fake SFTP, not protocol qualification.
Author: Abdelhalim Talbi.
"""
import os
import tempfile
import unittest
from pathlib import Path
from transfer_safety import upload_exclusive

class Remote:
    def __init__(self): self.data=bytearray()
    def __enter__(self): return self
    def __exit__(self,*_): return False
    def write(self,data): self.data.extend(data)

class SFTP:
    def __init__(self):
        self.remote=None; self.opened=[]; self.removed=[]
    def open(self,path,mode):
        self.opened.append((path,mode)); self.remote=Remote(); return self.remote
    def remove(self,path): self.removed.append(path)

class SourceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'source.bin'
        self.path.write_bytes(b'abcdefgh')
        self.sftp=SFTP()

    def upload(self,**kw):
        return upload_exclusive(self.sftp,self.path,'/upload/test.bin',chunk_size=4,**kw)

    def test_unmodified_file_succeeds(self):
        self.assertEqual(self.upload(),8)
        self.assertEqual(bytes(self.sftp.remote.data),b'abcdefgh')
        self.assertEqual(self.sftp.removed,[])
        self.assertEqual(self.sftp.opened,[('/upload/test.bin','wbx')])

    def test_truncation_mid_upload_cleans_remote(self):
        def mutate(done,_):
            if done==4: self.path.write_bytes(b'abcd')
        with self.assertRaises(OSError): self.upload(callback=mutate)
        self.assertEqual(self.sftp.removed,['/upload/test.bin'])

    def test_same_size_rewrite_mid_upload_cleans_remote(self):
        def mutate(done,_):
            if done==4:
                self.path.write_bytes(b'12345678')
                info=self.path.stat()
                os.utime(self.path,ns=(info.st_atime_ns,info.st_mtime_ns+10_000_000))
        with self.assertRaises(OSError): self.upload(callback=mutate)
        self.assertEqual(self.sftp.removed,['/upload/test.bin'])

    def test_source_replaced_with_same_size_is_rejected(self):
        def mutate(done,_):
            if done==4:
                replacement=self.path.with_suffix('.new')
                replacement.write_bytes(b'87654321')
                os.replace(replacement,self.path)
        with self.assertRaises(OSError): self.upload(callback=mutate)
        self.assertEqual(self.sftp.removed,['/upload/test.bin'])

    def test_source_deleted_mid_upload_is_rejected(self):
        def mutate(done,_):
            if done==4: self.path.unlink()
        with self.assertRaises(OSError): self.upload(callback=mutate)
        self.assertEqual(self.sftp.removed,['/upload/test.bin'])

    def test_symlink_source_rejected_before_remote_open(self):
        target=self.path.with_suffix('.link')
        try: target.symlink_to(self.path)
        except (OSError,NotImplementedError) as exc:
            self.skipTest('symlink unavailable: '+type(exc).__name__)
        with self.assertRaises(ValueError):
            upload_exclusive(self.sftp,target,'/upload/test.bin')
        self.assertEqual(self.sftp.opened,[])

    def test_cancelled_transfer_cleans_remote(self):
        with self.assertRaises(InterruptedError):
            self.upload(cancelled=lambda: bool(self.sftp.remote and self.sftp.remote.data))
        self.assertEqual(self.sftp.removed,['/upload/test.bin'])

if __name__=='__main__': unittest.main()
