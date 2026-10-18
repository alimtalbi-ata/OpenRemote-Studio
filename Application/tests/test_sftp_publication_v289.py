import tempfile
import unittest
from pathlib import Path
from transfer_safety import download_atomic

class FakeSftp:
    def __init__(self, payload=b'new', on_get=None):
        self.payload=payload
        self.on_get=on_get
    def get(self, remote, local, callback=None):
        Path(local).write_bytes(self.payload)
        if self.on_get:self.on_get()
        if callback:callback(len(self.payload),len(self.payload))

class AtomicCancellationTests(unittest.TestCase):
    def test_cancel_before_start_preserves_original(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file';p.write_bytes(b'old')
            with self.assertRaises(InterruptedError):
                download_atomic(FakeSftp(),'remote',p,cancelled=lambda:True)
            self.assertEqual(p.read_bytes(),b'old')
    def test_cancel_after_get_before_publish_preserves_original(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file';p.write_bytes(b'old');state={'cancel':False}
            with self.assertRaises(InterruptedError):
                download_atomic(FakeSftp(on_get=lambda:state.update(cancel=True)),'remote',p,cancelled=lambda:state['cancel'])
            self.assertEqual(p.read_bytes(),b'old')
            self.assertEqual(list(Path(d).glob('*.part')),[])
    def test_success_replaces_original(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file';p.write_bytes(b'old')
            download_atomic(FakeSftp(),'remote',p,cancelled=lambda:False)
            self.assertEqual(p.read_bytes(),b'new')
