import unittest
from ssh_hop_diagnostics import hop_status,route_stages,STAGES

class HopDiagnosticsTests(unittest.TestCase):
    def test_direct(self):self.assertEqual(route_stages(None),STAGES[3:])
    def test_jump(self):self.assertEqual(route_stages({'mode':'ssh_jump'}),STAGES)
    def test_reject_rds(self):
        with self.assertRaises(ValueError):route_stages({'mode':'rd_gateway'})
    def test_status(self):self.assertEqual(hop_status('target_connect','ok'),'SSH/target_connect: ok')
    def test_reject_unknown_stage(self):
        with self.assertRaises(ValueError):hop_status('host:password','ok')
    def test_reject_unknown_outcome(self):
        with self.assertRaises(ValueError):hop_status('target_pty','secret')
    def test_no_sensitive_route_data(self):
        route={'mode':'ssh_jump','jump_host':'sensitive.example','jump_user':'privateuser','vault_ref':'vault://private'}
        rendered=' '.join(hop_status(s,'starting') for s in route_stages(route))
        for secret in ('sensitive','privateuser','vault://'):self.assertNotIn(secret,rendered)
