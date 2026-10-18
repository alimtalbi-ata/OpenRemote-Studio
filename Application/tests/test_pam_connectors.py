import unittest
from pam_connectors import PamConnector,ConnectorRegistry
from launch_plan import build_launch_plan

class PamConnectorTests(unittest.TestCase):
 def setUp(self):
  self.profile={'name':'Prod','provider':'cyberark','endpoint':'https://pam.example'}
 def test_registered_profile_is_not_a_live_connector(self):
  result=ConnectorRegistry([self.profile]).inspect('cyberark:Safe/Account')
  self.assertFalse(result['ready'])
  self.assertFalse(result['authorized'])
  self.assertEqual(result['profiles'],['Prod'])
 def test_unknown_provider_profile_fails_closed(self):
  self.assertFalse(ConnectorRegistry([self.profile]).inspect('delinea:Account')['ready'])
 def test_no_implicit_session(self):
  with self.assertRaises(PermissionError):ConnectorRegistry([self.profile]).open_session('cyberark:Safe/Account', 'server')
 def test_no_pam_is_not_a_broker(self):
  registry=ConnectorRegistry([])
  self.assertTrue(registry.inspect('')['ready'])
  with self.assertRaises(PermissionError):registry.open_session('', 'server')
 def test_capabilities_are_all_false(self):
  connector=PamConnector(self.profile)
  self.assertFalse(connector.capabilities.authentication)
  self.assertFalse(connector.capabilities.authorization)
  self.assertFalse(connector.capabilities.session_broker)
  with self.assertRaises(NotImplementedError):connector.authenticate({})
 def test_web_pam_must_not_bypass_preflight(self):
  c={'protocol':'WEB','host':'https://example.org','port':'','user':''}
  plan=build_launch_plan(c,{'mode':'direct','vault_ref':'cyberark:Safe/A'},which=lambda _: '/usr/bin/tool',platform='nt')
  self.assertFalse(plan['ready'])
  self.assertIn('PAM', ' '.join(plan['issues']))
