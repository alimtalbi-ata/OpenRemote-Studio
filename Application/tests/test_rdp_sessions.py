
import os,tempfile,time,unittest
from pathlib import Path
from rdp_sessions import write_session,cleanup_stale
class RdpSessionsTests(unittest.TestCase):
 def test_file_encoding_and_gateway(self):
  with tempfile.TemporaryDirectory() as d:
   p=write_session(d,'server.example',route={'mode':'rd_gateway','gateway_host':'gw.example'})
   self.assertIn('gatewayhostname:s:gw.example:443',p.read_text(encoding='utf-16'))
   self.assertNotIn('password:s:',p.read_text(encoding='utf-16'))
 def test_invalid_host_creates_nothing(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):write_session(d,'invalid\nvalue')
   self.assertEqual(list(Path(d).iterdir()),[])
 def test_stale_cleanup(self):
  with tempfile.TemporaryDirectory() as d:
   p=write_session(d,'server.example')
   os.utime(p,(time.time()-90000,time.time()-90000))
   unrelated=Path(d)/'other.rdp';unrelated.write_text('retain')
   self.assertEqual(cleanup_stale(d),1)
   self.assertTrue(unrelated.exists())
 def test_new_file_retained(self):
  with tempfile.TemporaryDirectory() as d:
   p=write_session(d,'server.example')
   self.assertEqual(cleanup_stale(d),0)
   self.assertTrue(p.exists())
 def test_private_permissions_posix(self):
  if os.name!='posix':self.skipTest('POSIX only')
  with tempfile.TemporaryDirectory() as d:
   p=write_session(d,'server.example')
   self.assertEqual(p.stat().st_mode & 0o077,0)
 def test_symlink_not_deleted(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'target';target.write_text('retain')
   link=Path(d)/'openremote-rdp-link.rdp'
   try:link.symlink_to(target)
   except OSError:self.skipTest('symlinks unavailable')
   self.assertEqual(cleanup_stale(d,now=time.time()+90000),0)
   self.assertTrue(target.exists())
