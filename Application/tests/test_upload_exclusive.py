
import tempfile,unittest
from pathlib import Path
from transfer_safety import upload_exclusive
class Remote:
 def __init__(self,owner,fail=False):self.owner=owner;self.fail=fail
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def write(self,data):
  if self.fail:raise OSError('write failed')
  self.owner.data+=data
class FakeSFTP:
 def __init__(self,exists=False,fail=False):self.exists=exists;self.fail=fail;self.data=b'';self.removed=[];self.mode=None
 def open(self,path,mode):
  self.mode=mode
  if self.exists:raise FileExistsError(path)
  self.exists=True
  return Remote(self,self.fail)
 def remove(self,path):self.removed.append(path);self.exists=False
class UploadTests(unittest.TestCase):
 def test_upload_exclusive(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x';p.write_bytes(b'abcdef')
   s=FakeSFTP();progress=[]
   self.assertEqual(upload_exclusive(s,p,'/x',lambda done,total:progress.append((done,total)),2),6)
   self.assertEqual(s.data,b'abcdef');self.assertEqual(s.mode,'wbx');self.assertEqual(progress[-1],(6,6))
 def test_existing_not_removed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x';p.write_bytes(b'new');s=FakeSFTP(exists=True)
   with self.assertRaises(FileExistsError):upload_exclusive(s,p,'/x')
   self.assertEqual(s.removed,[])
 def test_failed_write_cleanup(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x';p.write_bytes(b'new');s=FakeSFTP(fail=True)
   with self.assertRaises(OSError):upload_exclusive(s,p,'/x')
   self.assertEqual(s.removed,['/x'])
 def test_invalid_chunk_size(self):
  with self.assertRaises(ValueError):upload_exclusive(FakeSFTP(),'notthere','/x',chunk_size=0)
