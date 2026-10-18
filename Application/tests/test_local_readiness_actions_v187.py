import unittest
from local_readiness_actions import repair_guidance

class LocalReadinessActionsTests(unittest.TestCase):
    def report(self, rows):
        return {"scope":"local_only","network_tested":False,"rows":rows}
    def test_missing_ssh(self):
        self.assertIn('OpenSSH',repair_guidance(self.report([{"protocol":"SSH","ready":False}])))
    def test_ready_no_changes(self):
        self.assertIn('Aucune correction',repair_guidance(self.report([{"protocol":"SSH","ready":True}])))
    def test_vnc_licensing(self):
        self.assertIn('licence',repair_guidance(self.report([{"protocol":"VNC","ready":False}])))
    def test_deduplication(self):
        self.assertEqual(repair_guidance(self.report([{"protocol":"RDP","ready":False}]*2)).count('RDP :'),1)
    def test_reject_remote_scope(self):
        with self.assertRaises(ValueError): repair_guidance({"scope":"remote","network_tested":False,"rows":[]})
    def test_reject_network_probe(self):
        with self.assertRaises(ValueError): repair_guidance({"scope":"local_only","network_tested":True,"rows":[]})
    def test_reject_unknown_protocol(self):
        with self.assertRaises(ValueError): repair_guidance(self.report([{"protocol":"TELNET"}]))
    def test_reject_oversized(self):
        with self.assertRaises(ValueError): repair_guidance(self.report([{"protocol":"SSH"}]*33))
