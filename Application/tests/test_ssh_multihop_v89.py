import unittest
from gateways import validate_route,parse_jump_chain
from ssh_hop_diagnostics import route_stages,hop_status
from access_preview import describe_path

class MultiHopTests(unittest.TestCase):
    def test_parse_two(self):
        self.assertEqual([h['host'] for h in parse_jump_chain('ops@b2:2222,b3')],['b2','b3'])
    def test_max_hops(self):
        with self.assertRaises(ValueError):parse_jump_chain('a,b,c,d')
    def test_reject_password_syntax(self):
        for value in ('user:secret@host','u@host;id','u@@host','-bad@host','a,,b','a,a','a:99999'):
            with self.subTest(value=value),self.assertRaises(ValueError):parse_jump_chain(value)
    def test_direct_disallows_chain(self):
        with self.assertRaises(ValueError):validate_route({'mode':'direct','jump_chain':'a'})
    def test_route_preserves_chain(self):
        route=validate_route({'mode':'ssh_jump','jump_host':'b1','jump_chain':'u@b2:2200'})
        self.assertEqual(route['jump_chain'],'u@b2:2200')
    def test_diagnostic_stages(self):
        stages=route_stages({'mode':'ssh_jump','jump_chain':'a,b'})
        self.assertIn('bastion_2_connect',stages)
        self.assertIn('bastion_3_tunnel',stages)
        self.assertEqual(hop_status('bastion_3_connect','ok'),'SSH/bastion_3_connect: ok')
    def test_preview(self):
        path=' '.join(describe_path({'protocol':'SSH','host':'target'}, {'mode':'ssh_jump','jump_host':'b1','jump_chain':'b2,b3'}))
        self.assertLess(path.index('b1'),path.index('b2'))
        self.assertLess(path.index('b2'),path.index('b3'))
