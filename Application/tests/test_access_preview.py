import tempfile,unittest
from pathlib import Path
from access_preview import describe_path
from rdp_sessions import write_session
class AccessPreviewTests(unittest.TestCase):
 def test_direct(self):
  lines=describe_path({'protocol':'RDP','host':'server.example'}, {'mode':'direct'})
  self.assertIn('Poste → server.example',lines[0])
 def test_gateway(self):
  lines=describe_path({'protocol':'RDP','host':'server.example'}, {'mode':'rd_gateway','gateway_host':'gw.example'})
  self.assertIn('RD Gateway gw.example:443',lines[0])
 def test_rds_collection(self):
  lines=describe_path({'protocol':'RDP','host':'server.example'}, {'mode':'rds_collection','gateway_host':'gw.example','collection':'Finance'})
  self.assertIn('collection RDS Finance',lines[0])
 def test_ssh_jump(self):
  lines=describe_path({'protocol':'SSH','host':'server.example'}, {'mode':'ssh_jump','jump_host':'jump.example'})
  self.assertIn('bastion SSH jump.example:22',lines[0])
 def test_pam_is_only_reference(self):
  lines=describe_path({'protocol':'RDP','host':'server.example'}, {'mode':'direct','vault_ref':'secret-id-1'})
  self.assertIn('référence documentaire',lines[-1])
 def test_rdp_session_written(self):
  with tempfile.TemporaryDirectory() as d:
   f=write_session(d,'server.example')
   self.assertTrue(Path(f).exists())
