import unittest
from ssh_path_editor import route_to_hops,validate_path,hops_to_route,path_preview

class TestSSHPathEditorV93(unittest.TestCase):
    def setUp(self):
        self.hops=[dict(host='bastion.local',port=22,user='admin'),dict(host='relay.local',port=2222,user='ops')]
    def test_round_trip(self):
        route=hops_to_route(self.hops,{'vault_ref':'PAM-REFERENCE'})
        self.assertEqual(route_to_hops(route),self.hops)
        self.assertEqual(route['vault_ref'],'PAM-REFERENCE')
    def test_primary_reordered(self):
        reversed_hops=list(reversed(self.hops))
        self.assertEqual(route_to_hops(hops_to_route(reversed_hops)),reversed_hops)
    def test_duplicate_primary_extra(self):
        with self.assertRaises(ValueError):validate_path([self.hops[0],dict(self.hops[0])])
    def test_duplicate_case_insensitive(self):
        with self.assertRaises(ValueError):validate_path([self.hops[0],dict(host='BASTION.LOCAL',port=22,user='other')])
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):validate_path([])
    def test_too_many_rejected(self):
        with self.assertRaises(ValueError):validate_path(self.hops*3)
    def test_single_primary(self):
        self.assertEqual(hops_to_route(self.hops[:1])['jump_chain'],'')
    def test_preview(self):
        preview=path_preview(self.hops,'target.local')
        self.assertIn('target.local',preview)
        self.assertIn('bastion.local',preview)
    def test_invalid_host(self):
        with self.assertRaises(ValueError):validate_path([dict(host='-invalid',port=22,user='admin')])
    def test_non_ssh_route(self):
        with self.assertRaises(ValueError):route_to_hops({'mode':'direct'})
