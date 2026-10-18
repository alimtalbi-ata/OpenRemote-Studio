import unittest
from pam_refs import parse_reference,capability_report,PROVIDERS
class PamRefTests(unittest.TestCase):
 def test_all_providers(self):
  for name in PROVIDERS:
   with self.subTest(name=name):
    self.assertEqual(parse_reference(name+':safe/account-01').provider,name)
 def test_empty(self):
  self.assertIsNone(parse_reference(''))
  self.assertFalse(capability_report('')['configured'])
 def test_secrets_rejected(self):
  for value in ('cyberark:password=abc','cyberark:https://vault','delinea:token=abc','beyondtrust:a@b'):
   with self.subTest(value=value),self.assertRaises(ValueError):parse_reference(value)
 def test_invalid_paths(self):
  for value in ('cyberark:../x','generic:a//b','unknown:item','cyberark:'):
   with self.subTest(value=value),self.assertRaises(ValueError):parse_reference(value)
 def test_never_claims_live_access(self):
  report=capability_report('cyberark:Safe/Account')
  self.assertTrue(report['configured'])
  self.assertFalse(report['secret_access'])
  self.assertFalse(report['session_broker'])
 def test_no_plain_secret_storage(self):
  self.assertNotIn('password',''.join(PROVIDERS))
