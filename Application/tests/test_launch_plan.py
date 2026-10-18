import unittest
from launch_plan import build_launch_plan
class LaunchPlanTests(unittest.TestCase):
 def conn(self,proto='SSH',port='22',user='admin'):
  return {'protocol':proto,'host':'server.example','port':port,'user':user}
 def test_ssh_jump(self):
  p=build_launch_plan(self.conn(),{'mode':'ssh_jump','jump_host':'jump.example'},which=lambda x:'/bin/'+x,platform='posix')
  self.assertTrue(p['ready']);self.assertIn('-J',p['args'])
 def test_rdp_requires_windows(self):
  self.assertFalse(build_launch_plan(self.conn('RDP'),which=lambda x:'/bin/'+x,platform='posix')['ready'])
 def test_invalid_port(self):
  with self.assertRaises(ValueError):build_launch_plan(self.conn(port='99999'),which=lambda x:'/bin/'+x,platform='posix')
 def test_invalid_user(self):
  with self.assertRaises(ValueError):build_launch_plan(self.conn(user='-oProxyCommand=bad'),which=lambda x:'/bin/'+x,platform='posix')
 def test_missing_client(self):
  self.assertFalse(build_launch_plan(self.conn('SFTP'),which=lambda _:None,platform='posix')['ready'])
 def test_rdp_gateway(self):
  p=build_launch_plan(self.conn('RDP'),{'mode':'rd_gateway','gateway_host':'gw.example','vault_ref':'cyberark:Safe/Account'},which=lambda _:'mstsc',platform='nt')
  self.assertFalse(p['ready']);self.assertIsNone(p['args']);self.assertTrue(p['issues'])
