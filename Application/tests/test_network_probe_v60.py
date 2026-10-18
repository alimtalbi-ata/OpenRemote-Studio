import unittest
from network_probe import endpoint,probe
class Tests(unittest.TestCase):
 def test_ssh_default(self):self.assertEqual(endpoint({'protocol':'SSH','host':'srv'}),('srv',22))
 def test_rdp_default(self):self.assertEqual(endpoint({'protocol':'RDP','host':'srv'}),('srv',3389))
 def test_web_url_sanitized(self):self.assertEqual(endpoint({'protocol':'WEB','host':'https://example.org/path?token=secret'}),('example.org',443))
 def test_credentials_rejected(self):
  with self.assertRaises(ValueError):endpoint({'protocol':'WEB','host':'https://user:pass@example.org'})
 def test_invalid_port(self):
  with self.assertRaises(ValueError):endpoint({'protocol':'SSH','host':'srv','port':65536})
 def test_success(self):
  class Sock:
   def close(self):pass
  self.assertTrue(probe({'protocol':'SSH','host':'srv'},connector=lambda addr,timeout:Sock())['reachable'])
 def test_failure(self):
  def fail(addr,timeout):raise OSError('down')
  self.assertFalse(probe({'protocol':'SSH','host':'srv'},connector=fail)['reachable'])
