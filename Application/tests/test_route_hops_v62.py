import unittest
from network_probe import route_hops

class RouteHopTests(unittest.TestCase):
 def setUp(self):self.conn={'protocol':'SSH','host':'target.example','port':22}
 def test_direct(self):
  hops=route_hops(self.conn,{})
  self.assertEqual(len(hops),1)
  self.assertEqual(hops[0]['role'],'cible')
 def test_jump(self):
  hops=route_hops(self.conn,{'mode':'ssh_jump','jump_host':'bastion.example','jump_port':'2222'})
  self.assertEqual([(h['host'],h['port']) for h in hops],[('bastion.example',2222),('target.example',22)])
  self.assertIn('sans traverser',hops[1]['scope'])
 def test_gateway(self):
  hops=route_hops({'protocol':'RDP','host':'server.example'}, {'mode':'rd_gateway','gateway_host':'gw.example'})
  self.assertEqual([(h['host'],h['port']) for h in hops],[('gw.example',443),('server.example',3389)])
 def test_collection(self):
  hops=route_hops({'protocol':'RDP','host':'server.example'}, {'mode':'rds_collection','gateway_host':'gw.example','collection':'Desktop'})
  self.assertEqual(hops[0]['role'],'passerelle RD Gateway')
 def test_invalid(self):
  with self.assertRaises(ValueError):route_hops(self.conn,{'mode':'ssh_jump','jump_host':'bad host'})
 def test_no_credentials(self):
  hops=route_hops(self.conn,{'mode':'ssh_jump','jump_host':'jump.example','jump_user':'admin','vault_ref':'vault://example'})
  self.assertNotIn('admin',str(hops))
  self.assertNotIn('vault://',str(hops))
