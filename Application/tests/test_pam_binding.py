import unittest
from pam_binding import resolve_pam_profile
from access_preflight import inspect_access
from launch_plan import build_launch_plan
class PamBindingTests(unittest.TestCase):
 def test_provider_matching(self):
  profiles=[{'name':'A','provider':'cyberark'},{'name':'B','provider':'delinea'}]
  result=resolve_pam_profile('cyberark:Safe/Account',profiles)
  self.assertEqual(result['profiles'],['A']);self.assertFalse(result['ready'])
 def test_unmatched_is_blocked(self):
  self.assertFalse(resolve_pam_profile('delinea:Safe',[])['ready'])
 def test_no_reference_ready(self):
  self.assertTrue(resolve_pam_profile('',[])['ready'])
 def test_pam_preflight_fails_closed(self):
  c={'protocol':'SSH','host':'server.example','port':'22','user':'admin'}
  r=inspect_access(c,{'mode':'direct','vault_ref':'cyberark:Safe/A'},which=lambda _: '/bin/ssh',platform='nt')
  self.assertFalse(r['ready']);self.assertTrue(any('PAM' in x for x in r['issues']))
 def test_pam_launch_fails_closed(self):
  c={'protocol':'SSH','host':'server.example','port':'22','user':'admin'}
  r=build_launch_plan(c,{'mode':'direct','vault_ref':'cyberark:Safe/A'},which=lambda _: '/bin/ssh',platform='nt')
  self.assertFalse(r['ready'])
 def test_direct_still_ready(self):
  c={'protocol':'SSH','host':'server.example','port':'22','user':'admin'}
  r=build_launch_plan(c,{'mode':'direct'},which=lambda _: '/bin/ssh',platform='nt')
  self.assertTrue(r['ready'])
