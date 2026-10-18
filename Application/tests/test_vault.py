import unittest,tempfile
from pathlib import Path
from vault import Vault
class VaultTests(unittest.TestCase):
 def test_roundtrip_and_wrong_password(self):
  with tempfile.TemporaryDirectory() as tmp:
   v=Vault(Path(tmp)/'secrets.enc');v.save({'server-1':'s3cr3t'},'long strong password 123')
   self.assertEqual(v.load('long strong password 123'),{'server-1':'s3cr3t'})
   self.assertNotIn(b's3cr3t',v.path.read_bytes())
   with self.assertRaises(Exception):v.load('another long password')
 def test_short_password(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):Vault(Path(tmp)/'v').save({},'short')
