
import ast,unittest
from pathlib import Path
from connection_policy import connection_route
class PolicyTests(unittest.TestCase):
 def test_direct(self):
  self.assertEqual(connection_route('SSH',{})['mode'],'')
 def test_rdp_gateway(self):
  self.assertEqual(connection_route('RDP',{'mode':'rd_gateway','gateway_host':'gw.example'})['mode'],'rd_gateway')
 def test_reject_rds_on_ssh(self):
  with self.assertRaises(ValueError):connection_route('SSH',{'mode':'rd_gateway','gateway_host':'gw.example'})
 def test_reject_jump_on_rdp(self):
  with self.assertRaises(ValueError):connection_route('RDP',{'mode':'ssh_jump','jump_host':'bastion'})
 def test_integrated_sftp_rejects_jump(self):
  with self.assertRaises(ValueError):connection_route('SFTP',{'mode':'ssh_jump','jump_host':'bastion'},integrated=True)
 def test_close_event_is_unique(self):
  code=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  tree=ast.parse(code)
  main=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Main')
  self.assertEqual(sum(isinstance(n,ast.FunctionDef) and n.name=='closeEvent' for n in main.body),1)
 def test_ssh_tab_uses_jump(self):
  code=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  body=code.split('    def ssh_tab(self):')[1].split('    def split_view(self):')[0]
  self.assertIn('ssh_jump_args',body)
