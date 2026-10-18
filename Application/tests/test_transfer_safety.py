
import tempfile,unittest
from pathlib import Path
from transfer_safety import download_atomic,remote_exists
class FakeSFTP:
 def __init__(self,fail=False):self.fail=fail
 def get(self,remote,local,callback=None):
  Path(local).write_bytes(b'partial' if self.fail else b'new content')
  if self.fail:raise OSError('network interrupted')
  if callback:callback(11,11)
 def stat(self,path):
  if path=='existing':return object()
  raise FileNotFoundError(path)
class TransferTests(unittest.TestCase):
 def test_atomic_download(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'data.txt';p.write_bytes(b'old')
   download_atomic(FakeSFTP(),'remote',p)
   self.assertEqual(p.read_bytes(),b'new content')
   self.assertFalse(list(Path(d).glob('*.part')))
 def test_failure_preserves_original(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'data.txt';p.write_bytes(b'old')
   with self.assertRaises(OSError):download_atomic(FakeSFTP(True),'remote',p)
   self.assertEqual(p.read_bytes(),b'old')
   self.assertEqual(len(list(Path(d).iterdir())),1)
 def test_missing_parent(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(FileNotFoundError):
    download_atomic(FakeSFTP(),'remote',Path(d)/'missing'/'file')
 def test_remote_exists(self):
  self.assertTrue(remote_exists(FakeSFTP(),'existing'))
  self.assertFalse(remote_exists(FakeSFTP(),'missing'))
