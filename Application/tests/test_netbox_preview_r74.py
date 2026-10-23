"""R74 comparison contract: offline, collisions, privacy and no mutation."""
import copy
import unittest
from netbox_preview import NetBoxPreviewError, compare_inventory


def snapshot(*devices):
    return {'state': 'ok', 'devices': list(devices), 'read_only': True}


def device(id, name, ip=''):
    return {'id': id, 'name': name, 'primary_ip4': ip}


def conn(host, protocol='SSH', **extra):
    return {'host': host, 'protocol': protocol, **extra}


class NetBoxPreviewR74Tests(unittest.TestCase):
    def test_offline_never_exposes_local_inventory(self):
        self.assertEqual(compare_inventory({'state': 'offline'}, [conn('private.local')]),
                         {'state': 'offline', 'read_only': True, 'rows': [], 'counts': {}})

    def test_hostname_match_case_and_trailing_dot(self):
        result = compare_inventory(snapshot(device(1, 'Server.Example')), [conn('server.example.')])
        self.assertEqual(result['counts']['matched'], 1)
        self.assertEqual(result['rows'][0]['local_host'], 'server.example')

    def test_ip_address_matches_cidr(self):
        result = compare_inventory(snapshot(device(1, 'device-1', '192.0.2.5/24')),
                                   [conn('192.0.2.5', 'RDP')])
        self.assertEqual(result['counts']['matched'], 1)

    def test_missing_local_and_local_only(self):
        result = compare_inventory(snapshot(device(1, 'remote.example')),
                                   [conn('other.example')])
        self.assertEqual(result['counts']['missing_local'], 1)
        self.assertEqual(result['counts']['local_only'], 1)

    def test_duplicate_netbox_name_ambiguous(self):
        result = compare_inventory(snapshot(device(1, 'shared'), device(2, 'shared')),
                                   [conn('shared')])
        self.assertEqual(result['counts']['ambiguous'], 2)
        self.assertEqual(result['counts']['matched'], 0)

    def test_duplicate_local_hosts_ambiguous(self):
        result = compare_inventory(snapshot(device(1, 'shared')),
                                   [conn('shared', 'SSH'), conn('shared', 'RDP')])
        self.assertEqual(result['counts']['ambiguous'], 1)

    def test_name_ip_collision_is_ambiguous(self):
        result = compare_inventory(snapshot(device(1, 'server', '192.0.2.7/24'),
                                            device(2, '192.0.2.7')),
                                   [conn('192.0.2.7')])
        self.assertEqual(result['counts']['ambiguous'], 2)

    def test_no_secret_in_output_and_no_mutation(self):
        source = [conn('safe.example', 'SSH', user='topsecret', tags='password=topsecret'),
                  conn('https://private.example/?token=topsecret', 'WEB')]
        before = copy.deepcopy(source)
        result = compare_inventory(snapshot(device(1, 'safe.example')), source)
        self.assertNotIn('topsecret', repr(result))
        self.assertEqual(source, before)

    def test_malformed_snapshot_and_duplicate_ids_fail_closed(self):
        for data in ({'state': 'error', 'devices': []}, snapshot(device(1, 'ok'), device(1, 'duplicate')),
                     snapshot({'id': True, 'name': 'bad'})):
            with self.subTest(data=data), self.assertRaises(NetBoxPreviewError):
                compare_inventory(data, [])

    def test_unsupported_and_malformed_hosts_not_displayed(self):
        result = compare_inventory(snapshot(device(1, 'safe')),
                                   [conn('safe'), conn('evil@host'), conn('https://secret/path', 'WEB')])
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['counts']['matched'], 1)

    def test_no_credentials_or_network_io(self):
        class Poison(dict):
            def __getitem__(self, key):
                if key in ('user', 'password', 'token'):
                    raise AssertionError('credential access')
                return super().__getitem__(key)
        self.assertEqual(compare_inventory(snapshot(device(1, 'safe')),
                                           [Poison(host='safe', protocol='SSH', user='secret')])['counts']['matched'], 1)


if __name__ == '__main__':
    unittest.main()
