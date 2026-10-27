"""R131: SSH trust-store preflight precedes any credential-provider call.

All data is synthetic; the fake transport does not make a network connection.
Author: Abdelhalim Talbi.
"""
import tempfile
import unittest
from pathlib import Path

from ssh_security import CredentialRef
from ssh_transport import SSHSettings, create_ssh_client


class FakeClient:
    def __init__(self, events, *, reject_host_file=False):
        self.events = events
        self.reject_host_file = reject_host_file
        self.closed = False
        self.host_path = None
        self.connect_kwargs = None

    def load_host_keys(self, path):
        self.events.append('load_host_keys')
        self.host_path = path
        if self.reject_host_file:
            raise ValueError('synthetic malformed known_hosts')

    def load_system_host_keys(self):
        self.events.append('load_system_host_keys')

    def set_missing_host_key_policy(self, policy):
        self.events.append('install_host_key_policy')

    def connect(self, **kwargs):
        self.events.append('connect')
        self.connect_kwargs = kwargs

    def close(self):
        self.events.append('close')
        self.closed = True


class SSHHostKeyPreflightR131Tests(unittest.TestCase):
    def invoke(self, path, *, client=None, events=None, provider_events=None, provider=None):
        events = events if events is not None else []
        provider_events = provider_events if provider_events is not None else []
        client = client or FakeClient(events)

        def factory():
            events.append('client_factory')
            return client

        def resolve(identifier):
            provider_events.append(identifier)
            events.append('resolve_credential')
            return 'synthetic-password-only'

        actual_provider = provider if provider is not None else resolve
        result = create_ssh_client(
            SSHSettings('server.example', 'operator', known_hosts=path),
            credential_ref=CredentialRef('test://credential'),
            credential_provider=actual_provider,
            client_factory=factory,
            policy_factory=lambda: object(),
        )
        return result, events, provider_events

    def test_missing_known_hosts_stops_before_client_and_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = str(Path(folder) / 'missing_known_hosts')
            events, provider_events = [], []
            with self.assertRaises(FileNotFoundError):
                self.invoke(missing, events=events, provider_events=provider_events)
            self.assertEqual(events, [])
            self.assertEqual(provider_events, [])

    def test_empty_known_hosts_stops_before_client_and_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            empty = Path(folder) / 'known_hosts'
            empty.write_text('', encoding='utf-8')
            events, provider_events = [], []
            with self.assertRaisesRegex(ValueError, 'empty'):
                self.invoke(str(empty), events=events, provider_events=provider_events)
            self.assertEqual(events, [])
            self.assertEqual(provider_events, [])

    def test_host_file_load_failure_does_not_resolve_credential(self):
        with tempfile.TemporaryDirectory() as folder:
            key_file = Path(folder) / 'known_hosts'
            key_file.write_text('synthetic non-empty input\n', encoding='utf-8')
            events, provider_events = [], []
            client = FakeClient(events, reject_host_file=True)
            with self.assertRaisesRegex(ValueError, 'malformed'):
                self.invoke(str(key_file), client=client, events=events, provider_events=provider_events)
            self.assertEqual(provider_events, [])
            self.assertLess(events.index('load_host_keys'), events.index('close'))
            self.assertNotIn('resolve_credential', events)
            self.assertNotIn('connect', events)
            self.assertTrue(client.closed)

    def test_trust_material_and_policy_precede_provider_and_connect(self):
        with tempfile.TemporaryDirectory() as folder:
            key_file = Path(folder) / 'known_hosts'
            key_file.write_text('synthetic trusted-host record\n', encoding='utf-8')
            events, provider_events = [], []
            client = FakeClient(events)
            result, events, provider_events = self.invoke(
                str(key_file), client=client, events=events, provider_events=provider_events)
            self.assertIs(result, client)
            self.assertEqual(provider_events, ['test://credential'])
            self.assertLess(events.index('load_host_keys'), events.index('install_host_key_policy'))
            self.assertLess(events.index('install_host_key_policy'), events.index('resolve_credential'))
            self.assertLess(events.index('resolve_credential'), events.index('connect'))
            self.assertTrue(client.connect_kwargs['allow_agent'] is False)
            self.assertTrue(client.connect_kwargs['look_for_keys'] is False)

    def test_system_store_is_loaded_before_provider_when_no_explicit_file(self):
        events, provider_events = [], []
        client = FakeClient(events)
        result, events, provider_events = self.invoke(None, client=client, events=events, provider_events=provider_events)
        self.assertIs(result, client)
        self.assertLess(events.index('load_system_host_keys'), events.index('resolve_credential'))
        self.assertLess(events.index('install_host_key_policy'), events.index('resolve_credential'))
        self.assertEqual(provider_events, ['test://credential'])


if __name__ == '__main__':
    unittest.main()
