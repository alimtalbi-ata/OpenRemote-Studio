import unittest
from connection_path_diagnostics import topology,format_topology

class PathTests(unittest.TestCase):
    def test_direct(self):
        r=topology('SSH');self.assertEqual([n['kind'] for n in r['nodes']],['poste','cible']);self.assertFalse(r['network_tested'])
    def test_pam(self):
        r=topology('RDP',{'mode':'direct','vault_ref':'secret-path'});self.assertEqual(r['nodes'][1]['kind'],'pam');self.assertNotIn('secret-path',str(r))
    def test_ssh_chain(self):
        r=topology('SSH',{'mode':'ssh_jump','jump_host':'bastion.internal','jump_chain':'alice@second.internal:2222,third.internal'})
        self.assertEqual([n['kind'] for n in r['nodes']],['poste','bastion','bastion','bastion','cible'])
        self.assertNotIn('bastion.internal',str(r));self.assertNotIn('alice',str(r))
    def test_rd_gateway(self):
        r=topology('RDP',{'mode':'rd_gateway','gateway_host':'gateway.internal'});self.assertEqual(r['nodes'][1]['kind'],'rd_gateway')
    def test_rds_collection(self):
        r=topology('RDP',{'mode':'rds_collection','gateway_host':'gateway.internal','collection':'Desktop'});self.assertEqual(r['nodes'][-2]['kind'],'rds_collection')
    def test_invalid_route(self):
        with self.assertRaises(ValueError):topology('VNC',{'mode':'ssh_jump','jump_host':'jump.internal'})
    def test_invalid_protocol(self):
        with self.assertRaises(ValueError):topology('TELNET')
    def test_format(self):
        self.assertIn('Aucune étape testée',format_topology(topology('SFTP')))
    def test_no_fake_pass(self):
        self.assertTrue(all(n['status']=='non_verifie' for n in topology('WEB')['nodes']))
    def test_invalid_format(self):
        with self.assertRaises(ValueError):format_topology({'schema':'openremote.path.v1','network_tested':True,'credentials_accessed':False,'nodes':[]})
