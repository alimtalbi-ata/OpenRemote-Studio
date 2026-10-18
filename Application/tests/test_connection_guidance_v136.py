import unittest
from connection_guidance import GUIDES,guidance,format_guidance

class GuidanceTests(unittest.TestCase):
    def test_all_protocols_offline(self):
        for p in GUIDES:
            with self.subTest(p=p):
                r=guidance(p)
                self.assertFalse(r['network_tested'])
                self.assertFalse(r['remote_authenticated'])
                self.assertEqual(len(r['steps']),3)
    def test_pam(self):
        self.assertIn('PAM',guidance('SSH',pam=True)['steps'][-1])
    def test_failure(self):
        self.assertIn('codes de sortie',guidance('RDP',failures=2)['steps'][-1])
    def test_unknown(self):
        self.assertIn('pas observée',guidance('VNC',unknown=1)['steps'][-1])
    def test_local_unready(self):
        self.assertIn('prérequis locaux',guidance('SFTP',local_ready=False)['steps'][0])
    def test_unsupported(self):
        with self.assertRaises(ValueError):guidance('TELNET')
    def test_negative(self):
        with self.assertRaises(ValueError):guidance('SSH',failures=-1)
    def test_format(self):
        txt=format_guidance(guidance('WEB'))
        self.assertIn('Aucun test réseau effectué',txt)
    def test_invalid_format(self):
        with self.assertRaises(ValueError):format_guidance({'protocol':'SSH','network_tested':True})
