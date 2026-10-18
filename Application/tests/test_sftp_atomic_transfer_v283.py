import tempfile
import unittest
from pathlib import Path
from sftp_atomic_transfer import download_atomic, TransferCancelled

class FakeSftp:
    def __init__(self, fail=False, on_get=None):
        self.fail=fail;self.on_get=on_get
    def get(self, remote, target):
        Path(target).write_bytes(b'new-content')
        if self.on_get:self.on_get()
        if self.fail:raise IOError('broken connection')

class AtomicTransferTests(unittest.TestCase):
    def test_success_replaces_existing_destination(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file';p.write_bytes(b'old')
            download_atomic(FakeSftp(),'remote',p)
            self.assertEqual(p.read_bytes(),b'new-content')
            self.assertEqual(sorted(x.name for x in Path(d).iterdir()),['file'])
    def test_failure_preserves_existing_destination(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file';p.write_bytes(b'old')
            with self.assertRaises(IOError):download_atomic(FakeSftp(fail=True),'remote',p)
            self.assertEqual(p.read_bytes(),b'old')
            self.assertEqual(len(list(Path(d).iterdir())),1)
    def test_cancel_before_start(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file'
            with self.assertRaises(TransferCancelled):download_atomic(FakeSftp(),'remote',p,lambda:True)
            self.assertFalse(p.exists())
    def test_cancel_after_transfer_preserves_existing_destination(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file';p.write_bytes(b'old');flag=[False]
            with self.assertRaises(TransferCancelled):
                download_atomic(FakeSftp(on_get=lambda:flag.__setitem__(0,True)),'remote',p,lambda:flag[0])
            self.assertEqual(p.read_bytes(),b'old')
            self.assertEqual(len(list(Path(d).iterdir())),1)
