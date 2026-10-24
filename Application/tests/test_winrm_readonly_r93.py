"""R93 WinRM read-only inventory tests; fake transport, no network/credentials."""
import json
import unittest
from winrm_readonly import WinRMError, WinRMReadOnly

ORIGIN = 'https://windows.example.test:5986'


def payload(disks=None):
    return {'os': {'Caption': 'Windows Server', 'Version': '10.0', 'BuildNumber': '20348',
                   'CSName': 'LAB-SRV'},
            'disks': [{'DeviceID': 'C:', 'Size': '10000', 'FreeSpace': '4000'}] if disks is None else disks}


class Reply:
    def __init__(self, body, status_code=0, stderr=b''):
        self.status_code = status_code
        self.std_out = body
        self.std_err = stderr


class FakeFactory:
    def __init__(self, response=None):
        self.calls = []
        self.scripts = []
        self.response = response or Reply(json.dumps(payload()).encode())

    def __call__(self, endpoint, username, password, *, timeout):
        self.calls.append((endpoint, username, password, timeout))
        return self

    def run_ps(self, script):
        self.scripts.append(script)
        return self.response


class WinRMReadOnlyR93Tests(unittest.TestCase):
    def test_offline_never_resolves_secrets_or_network(self):
        calls = []
        client = WinRMReadOnly(ORIGIN, 'operator', lambda: calls.append('secret'),
                               session_factory=lambda *a, **k: calls.append('network'))
        self.assertEqual(client.inventory()['state'], 'offline')
        self.assertEqual(calls, [])

    def test_https_origin_rejects_userinfo_paths_query_fragments_and_control(self):
        for value in ('http://windows.example.test', 'https://user:pass@windows.example.test',
                      'https://windows.example.test/wsman', 'https://windows.example.test/?token=abc',
                      'https://windows.example.test/#x', 'https://windows.example.test\n',
                      'https://windows.example.test:99999', 'https://windows..example.test',
                      'https://windows.example.test\\@evil.test'):
            with self.subTest(value=value), self.assertRaises(WinRMError):
                WinRMReadOnly(value, 'operator')

    def test_allowlisted_read_only_cim_queries_and_tls_endpoint(self):
        factory = FakeFactory()
        client = WinRMReadOnly('https://windows.example.test', 'operator',
                               lambda: 'TOPSECRET', session_factory=factory)
        result = client.inventory(online=True)
        self.assertEqual(factory.calls, [('https://windows.example.test:5986/wsman',
                                          'operator', 'TOPSECRET', 30)])
        self.assertEqual(result['disks'], [{'drive': 'C:', 'size_bytes': 10000, 'free_bytes': 4000}])
        self.assertTrue(result['read_only'])
        script = factory.scripts[0]
        self.assertEqual(len(factory.scripts), 1)
        self.assertIn('Get-CimInstance', script)
        self.assertNotIn('Set-', script)
        self.assertNotIn('TOPSECRET', script)
        self.assertNotIn('operator', script)

    def test_missing_provider_and_cancel_prevent_network(self):
        factory = FakeFactory()
        client = WinRMReadOnly(ORIGIN, 'operator', session_factory=factory)
        with self.assertRaisesRegex(WinRMError, 'credentials_required'):
            client.inventory(online=True)
        client = WinRMReadOnly(ORIGIN, 'operator', lambda: 'secret', session_factory=factory)
        with self.assertRaisesRegex(WinRMError, 'cancelled'):
            client.inventory(online=True, cancelled=lambda: True)
        self.assertEqual(factory.calls, [])

    def test_transport_and_remote_stderr_are_redacted(self):
        secret = 'PRIVATE_TOKEN_PASSWORD'
        def fail(*a, **kw):
            raise RuntimeError(secret)
        client = WinRMReadOnly(ORIGIN, 'operator', lambda: secret, session_factory=fail)
        with self.assertRaises(WinRMError) as caught:
            client.inventory(online=True)
        self.assertEqual(str(caught.exception), 'winrm_transport_unavailable')
        self.assertNotIn(secret, repr(client) + str(caught.exception))
        fake = FakeFactory(Reply(b'bad', status_code=1, stderr=secret.encode()))
        with self.assertRaisesRegex(WinRMError, 'remote_query_failed') as caught:
            WinRMReadOnly(ORIGIN, 'operator', lambda: secret, session_factory=fake).inventory(online=True)
        self.assertNotIn(secret, str(caught.exception))

    def test_invalid_and_oversized_responses_fail_closed(self):
        bad = [b'not-json', b'\xff', b'x'*65537,
               json.dumps(payload([{'DeviceID': 'C:', 'Size': 10, 'FreeSpace': 11}])).encode(),
               json.dumps(payload([{'DeviceID': 'C:', 'Size': 10, 'FreeSpace': 1},
                                   {'DeviceID': 'C:', 'Size': 10, 'FreeSpace': 1}])).encode(),
               json.dumps(payload([{'DeviceID': 'D:', 'Size': -1, 'FreeSpace': 0}])).encode()]
        for output in bad:
            with self.subTest(output=output[:25]):
                fake = FakeFactory(Reply(output))
                with self.assertRaisesRegex(WinRMError, 'invalid_response'):
                    WinRMReadOnly(ORIGIN, 'operator', lambda: 'secret',
                                  session_factory=fake).inventory(online=True)

    def test_invalid_timeout_username_and_response_shape(self):
        for value in (True, 0, 14, 61, 20.5, '30'):
            with self.subTest(timeout=value), self.assertRaises(WinRMError):
                WinRMReadOnly(ORIGIN, 'operator', timeout=value)
        for name in ('', 'bad\nname', ' space', 'name\x00'):
            with self.subTest(name=name), self.assertRaises(WinRMError):
                WinRMReadOnly(ORIGIN, name)
        fake = FakeFactory(Reply(json.dumps({'os': 'bad', 'disks': []}).encode()))
        with self.assertRaisesRegex(WinRMError, 'invalid_response'):
            WinRMReadOnly(ORIGIN, 'operator', lambda: 'secret', session_factory=fake).inventory(online=True)


if __name__ == '__main__':
    unittest.main()
