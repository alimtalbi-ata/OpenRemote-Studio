
import tempfile,unittest
from pathlib import Path
from gateways import validate_route,rdp_content,ssh_jump_args
from routes import RouteStore
class GatewayTests(unittest.TestCase):
 def test_rdp_gateway(self):
  content=rdp_content('srv.example','3389','DOMAIN\\user',
     {'mode':'rd_gateway','gateway_host':'rdgw.example'})
  self.assertIn('gatewayhostname:s:rdgw.example:443',content)
  self.assertNotIn('password',content.lower())
 def test_rds_collection(self):
  content=rdp_content('rds.example',route={'mode':'rds_collection',
        'gateway_host':'rdgw.example','collection':'Finance'})
  self.assertIn('tsv://MS Terminal Services Plugin.1.Finance',content)
 def test_jump(self):
  self.assertEqual(ssh_jump_args({'mode':'ssh_jump','jump_host':'bastion.example',
       'jump_user':'admin','jump_port':'2222'}),['-J','admin@bastion.example:2222'])
 def test_injection(self):
  for host in ['-evil','gateway\npassword:s:bad','foo/bar']:
   with self.subTest(host=host):
    with self.assertRaises(ValueError):validate_route({'mode':'rd_gateway','gateway_host':host})
 def test_route_persistence(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'routes.json'
   store=RouteStore(path)
   store.set_route('id-1',{'mode':'rd_gateway','gateway_host':'gw.example'})
   self.assertEqual(RouteStore(path).for_connection('id-1')['gateway_host'],'gw.example')
 def test_no_secret_in_route(self):
  route=validate_route({'mode':'rd_gateway','gateway_host':'gw.example','password':'do-not-store'})
  self.assertNotIn('password',route)
 def test_rdp_rejects_ssh_jump(self):
  with self.assertRaises(ValueError):rdp_content('server',route={'mode':'ssh_jump','jump_host':'bastion'})
