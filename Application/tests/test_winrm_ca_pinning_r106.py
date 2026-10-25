"""R106 compatibility tests for the pinned WinRM CA lifecycle.

Offline and injected transport only; no Windows Server or real credentials.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import tempfile
import unittest

from winrm_readonly import WinRMReadOnly, WinRMError
from winrm_services_readonly import WinRMServicesReadOnly

CA = Path(__file__).parent / 'fixtures' / 'r105-public-test-ca.pem'
ORIGIN = 'https://windows.example.test'


class CAPinningR106(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'enterprise-ca.pem'
        self.path.write_bytes(CA.read_bytes())
        self.calls = []

    def client(self, cls=WinRMReadOnly, provider=None):
        return cls(ORIGIN, 'readonly',
                   provider if provider is not None else self.password,
                   session_factory=self.transport, ca_bundle=str(self.path))

    def password(self):
        self.calls.append('credential')
        return 'TEST_SECRET_NOT_REAL'

    def transport(self, *args, **kwargs):
        self.calls.append('network')
        ca_path = kwargs.get('ca_bundle')
        if ca_path is not None:
            # R107+ passes a per-request trust copy, never the source path.
            self.snapshot_path = Path(ca_path)
            self.assertNotEqual(self.snapshot_path.resolve(), self.path.resolve())
            self.assertEqual(self.snapshot_path.read_bytes(), CA.read_bytes())
        raise RuntimeError('synthetic transport failure; no host is contacted')

    def test_inventory_change_blocks_credential_and_transport(self):
        client = self.client()
        self.path.write_bytes(self.path.read_bytes() + b'\n')
        with self.assertRaisesRegex(WinRMError, '^winrm_ca_bundle_changed$'):
            client.inventory(online=True)
        self.assertEqual(self.calls, [])

    def test_services_change_blocks_credential_and_transport(self):
        client = self.client(WinRMServicesReadOnly)
        self.path.write_bytes(self.path.read_bytes() + b'\n')
        with self.assertRaisesRegex(WinRMError, '^winrm_ca_bundle_changed$'):
            client.services(online=True)
        self.assertEqual(self.calls, [])

    def test_removed_ca_fails_closed_without_secret(self):
        client = self.client()
        self.path.unlink()
        with self.assertRaisesRegex(WinRMError, '^winrm_invalid_ca_bundle$'):
            client.inventory(online=True)
        self.assertEqual(self.calls, [])

    def test_symlink_swap_fails_closed_without_secret(self):
        client = self.client()
        self.path.unlink()
        try:
            self.path.symlink_to(CA)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaisesRegex(WinRMError, '^winrm_invalid_ca_bundle$'):
            client.inventory(online=True)
        self.assertEqual(self.calls, [])

    def test_change_during_credential_resolution_keeps_inflight_snapshot_pinned(self):
        def provider():
            self.calls.append('credential')
            self.path.write_bytes(self.path.read_bytes() + b'\n')
            return 'TEST_SECRET_NOT_REAL'

        client = self.client(provider=provider)
        # The snapshot was validated before credential resolution. Changing
        # the source cannot change the CA bytes already handed to transport.
        # A synthetic transport failure avoids contacting any remote host.
        with self.assertRaisesRegex(WinRMError, '^winrm_transport_unavailable$'):
            client.inventory(online=True)
        self.assertEqual(self.calls, ['credential', 'network'])
        self.assertFalse(self.snapshot_path.exists())

        # A later request must reject the changed source before WinCred/network.
        with self.assertRaisesRegex(WinRMError, '^winrm_ca_bundle_changed$'):
            client.inventory(online=True)
        self.assertEqual(self.calls, ['credential', 'network'])

    def test_offline_never_rechecks_or_resolves(self):
        client = self.client()
        self.path.unlink()
        self.assertEqual(client.inventory()['state'], 'offline')
        self.assertEqual(self.calls, [])

    def test_no_ca_uses_existing_transport_contract(self):
        client = WinRMReadOnly(ORIGIN, 'readonly', self.password,
                               session_factory=self.transport)
        with self.assertRaisesRegex(WinRMError, '^winrm_transport_unavailable$'):
            client.inventory(online=True)
        self.assertEqual(self.calls, ['credential', 'network'])

    def test_identical_bytes_remain_valid(self):
        client = self.client()
        self.path.write_bytes(CA.read_bytes())
        with self.assertRaisesRegex(WinRMError, '^winrm_transport_unavailable$'):
            client.inventory(online=True)
        self.assertEqual(self.calls, ['credential', 'network'])


if __name__ == '__main__':
    unittest.main()
