import unittest
from windows_client_health import inspect_clients

class WindowsClientHealthTests(unittest.TestCase):
    def test_all_clients_present_windows(self):
        report=inspect_clients(which=lambda name: 'C:/Windows/'+name+'.exe',platform='nt')
        self.assertEqual(report['ready_count'],4)
        self.assertFalse(report['network_tested'])
    def test_missing_client(self):
        report=inspect_clients(which=lambda name: None,platform='nt')
        self.assertEqual(report['ready_count'],0)
        self.assertTrue(all(r['status']=='Client absent' for r in report['rows']))
    def test_rdp_unsupported_posix(self):
        report=inspect_clients(which=lambda name: '/usr/bin/'+name,platform='posix')
        self.assertEqual(report['ready_count'],3)
        self.assertEqual(report['rows'][2]['status'],'Windows requis')
    def test_empty_resolution_is_absent(self):
        report=inspect_clients(which=lambda name: '  ',platform='nt')
        self.assertEqual(report['ready_count'],0)
    def test_invalid_platform(self):
        with self.assertRaises(ValueError):inspect_clients(platform='unknown')
    def test_protocol_order(self):
        self.assertEqual([r['protocol'] for r in inspect_clients(which=lambda name: None,platform='nt')['rows']],['SSH','SFTP','RDP','VNC'])
