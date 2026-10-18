import unittest
from network_probe import route_probe_notice
class RouteProbeTests(unittest.TestCase):
 def test_direct(self):self.assertIn('direct',route_probe_notice({'mode':'direct'}))
 def test_jump(self):
  text=route_probe_notice({'mode':'ssh_jump'})
  self.assertIn('rebond SSH',text)
  self.assertIn('ne traverse pas',text)
 def test_gateway(self):self.assertIn('RD Gateway',route_probe_notice({'mode':'rd_gateway'}))
 def test_unknown_fail_safe(self):self.assertIn('ne traverse pas',route_probe_notice({'mode':'unknown'}))
 def test_invalid(self):
  with self.assertRaises(ValueError):route_probe_notice(None)
