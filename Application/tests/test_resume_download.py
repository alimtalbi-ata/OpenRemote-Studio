
import io,tempfile,unittest
from pathlib import Path
from transfer_safety import download_resume_verified
class Remote:
 def __init__(self,data,cut=None):self.data=data;self.cut=cut
 def stat(self,path):return type('Stat',(),{'st_size':len(self.data)})()
 def open(self,path,mode):
  data=self.data if self.cut is None else self.data[:self.cut]
  return io.BytesIO(data)
class ResumeTests(unittest.TestCase):
 def test_fresh(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'file';n=download_resume_verified(Remote(b'abc'),'/file',target,'id')
   self.assertEqual(n,3);self.assertEqual(target.read_bytes(),b'abc')
 def test_resume_after_interruption(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'file';target.write_bytes(b'old')
   with self.assertRaises(OSError):download_resume_verified(Remote(b'abcdef',cut=3),'/file',target,'id',chunk_size=2)
   self.assertEqual(target.read_bytes(),b'old')
   self.assertEqual(len(list(Path(d).glob('*.part'))),1)
   download_resume_verified(Remote(b'abcdef'),'/file',target,'id',chunk_size=2)
   self.assertEqual(target.read_bytes(),b'abcdef')
   self.assertEqual(list(Path(d).glob('*.part')),[])
 def test_changed_prefix_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'file'
   with self.assertRaises(OSError):download_resume_verified(Remote(b'abcdef',cut=3),'/file',target,'id',chunk_size=2)
   with self.assertRaisesRegex(ValueError,'modifié'):
    download_resume_verified(Remote(b'ZZZdef'),'/file',target,'id',chunk_size=2)
   self.assertFalse(target.exists())
 def test_separate_identity(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'file'
   with self.assertRaises(OSError):download_resume_verified(Remote(b'abcdef',cut=2),'/file',target,'id1')
   download_resume_verified(Remote(b'abcdef'),'/file',target,'id2')
   self.assertEqual(target.read_bytes(),b'abcdef')
   self.assertEqual(len(list(Path(d).glob('*.part'))),1)
 def test_invalid_chunk(self):
  with self.assertRaises(ValueError):download_resume_verified(Remote(b''),'/x','/tmp/x','id',chunk_size=0)

class ChangingRemote(Remote):
 def __init__(self,data,second_size):
  super().__init__(data);self.calls=0;self.second_size=second_size
 def stat(self,path):
  self.calls+=1
  size=len(self.data) if self.calls==1 else self.second_size
  return type('Stat',(),{'st_size':size})()

class ResumePublishIntegrityTests(unittest.TestCase):
 def test_remote_size_change_blocks_publication(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'existing';target.write_bytes(b'old')
   with self.assertRaisesRegex(ValueError,'modifié'):
    download_resume_verified(ChangingRemote(b'abcdef',7),'/file',target,'id')
   self.assertEqual(target.read_bytes(),b'old')
   self.assertEqual(len(list(Path(d).glob('*.part'))),1)
 def test_boolean_remote_size_rejected(self):
  class BadRemote(Remote):
   def stat(self,path):return type('Stat',(),{'st_size':True})()
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):
    download_resume_verified(BadRemote(b'x'),'/file',Path(d)/'file','id')
