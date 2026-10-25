"""R107: pinned WinRM CA snapshot used only during the synchronous request.

Offline unit tests with a real public PEM and injected transports; no network.
Author: Abdelhalim Talbi.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from winrm_readonly import WinRMReadOnly, WinRMError
from winrm_services_readonly import WinRMServicesReadOnly

CA = Path(__file__).parent / 'fixtures' / 'r105-public-test-ca.pem'
ORIGIN = 'https://windows.example.test'


class Reply:
    status_code = 0
    std_err = b''
    std_out = json.dumps({'os': {'Caption': 'Windows', 'Version': '10',
                       'BuildNumber': '20348', 'CSName': 'LAB'}, 'disks': []}).encode()


class CASnapshotR107(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.original = Path(tmp.name) / 'original.pem'
        self.original.write_bytes(CA.read_bytes())
        self.snapshots = []

    def client(self, cls=WinRMReadOnly, factory=None, provider=None):
        return cls(ORIGIN, 'readonly', provider or (lambda: 'FAKE_ONLY'),
                   session_factory=factory or self.factory,
                   ca_bundle=str(self.original))

    def factory(self, endpoint, username, password, *, timeout, ca_bundle=None):
        self.assertEqual(password, 'FAKE_ONLY')
        self.assertIsNotNone(ca_bundle)
        snap = Path(ca_bundle)
        self.assertNotEqual(snap, self.original)
        self.assertTrue(snap.is_file())
        self.assertEqual(snap.read_bytes(), CA.read_bytes())
        if os.name != 'nt':
            self.assertEqual(snap.stat().st_mode & 0o077, 0)
            self.assertEqual(snap.parent.stat().st_mode & 0o077, 0)
        self.snapshots.append(snap)
        return self

    def run_ps(self, script):
        if 'Win32_Service' in script:
            result = Reply()
            result.std_out = b'{"TotalCount":0,"Services":[]}'
            return result
        return Reply()

    def test_inventory_uses_private_snapshot_and_cleans_up(self):
        self.assertEqual(self.client().inventory(online=True)['state'], 'ok')
        self.assertEqual(len(self.snapshots), 1)
        self.assertFalse(self.snapshots[0].exists())
        self.assertFalse(self.snapshots[0].parent.exists())

    def test_services_uses_private_snapshot_and_cleans_up(self):
        self.assertEqual(self.client(WinRMServicesReadOnly).services(online=True)['services'], [])
        self.assertFalse(self.snapshots[0].parent.exists())

    def test_original_mutation_during_factory_cannot_replace_snapshot(self):
        def factory(*args, **kwargs):
            result = self.factory(*args, **kwargs)
            self.original.write_text('INVALID AFTER SNAPSHOT')
            self.assertEqual(self.snapshots[0].read_bytes(), CA.read_bytes())
            return result
        client = self.client(factory=factory)
        self.assertEqual(client.inventory(online=True)['state'], 'ok')
        self.assertFalse(self.snapshots[0].exists())
        with self.assertRaisesRegex(WinRMError, '^winrm_invalid_ca_bundle$'):
            client.inventory(online=True)

    def test_transport_exception_redacted_and_snapshot_removed(self):
        def broken(*args, **kwargs):
            self.factory(*args, **kwargs)
            raise RuntimeError('FAKE_ONLY confidential')
        with self.assertRaisesRegex(WinRMError, '^winrm_transport_unavailable$') as ctx:
            self.client(factory=broken).inventory(online=True)
        self.assertNotIn('FAKE_ONLY', str(ctx.exception))
        self.assertFalse(self.snapshots[0].parent.exists())

    def test_provider_mutation_rejected_before_snapshot_or_transport(self):
        called = []
        def provider():
            self.original.write_bytes(self.original.read_bytes() + b'\n')
            return 'FAKE_ONLY'
        def factory(*args, **kwargs):
            called.append('network')
            return self
        client = self.client(provider=provider, factory=factory)
        with self.assertRaisesRegex(WinRMError, '^winrm_ca_bundle_changed$'):
            client.inventory(online=True)
        self.assertEqual(called, [])

    def test_offline_does_not_allocate_snapshot_or_request_credential(self):
        client = self.client(provider=lambda: self.fail('credential read offline'))
        with patch('winrm_readonly.tempfile.TemporaryDirectory',
                   side_effect=AssertionError('snapshot allocated offline')):
            self.assertEqual(client.inventory()['state'], 'offline')
        self.assertEqual(self.snapshots, [])


if __name__ == '__main__':
    unittest.main()
