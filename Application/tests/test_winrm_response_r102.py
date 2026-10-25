"""R102: actual backend tests for fail-closed WinRM reply parsing."""
import json
import unittest

from winrm_readonly import WinRMReadOnly, WinRMError
from winrm_services_readonly import WinRMServicesReadOnly

ORIGIN = 'https://windows.example.test:5986'
OS = {'os': {'Caption': 'Windows Server', 'Version': '10.0',
             'BuildNumber': '20348', 'CSName': 'LAB-SRV'}, 'disks': []}
SERVICES = {'TotalCount': 1, 'Services': [{'Name': 'Spooler',
             'DisplayName': 'Print Spooler', 'State': 'Running', 'StartMode': 'Auto'}]}


class Reply:
    def __init__(self, payload, status=0):
        self.std_out = payload
        self.status_code = status
        self.std_err = b'PRIVATE_PASSWORD_DO_NOT_LOG'


class Factory:
    def __init__(self, reply):
        self.reply = reply
        self.calls = 0

    def __call__(self, *_args, **_kwargs):
        self.calls += 1
        return self

    def run_ps(self, _script):
        return self.reply


class ExplodingReply:
    status_code = 0

    @property
    def std_out(self):
        raise RuntimeError('PRIVATE_PASSWORD_DO_NOT_LOG')


class WinRMResponseR102Tests(unittest.TestCase):
    def _query(self, klass, reply):
        factory = Factory(reply)
        client = klass(ORIGIN, 'operator', lambda: 'PRIVATE_PASSWORD_DO_NOT_LOG',
                       session_factory=factory)
        if klass is WinRMReadOnly:
            return client.inventory(online=True)
        return client.services(online=True)

    def test_valid_payloads_both_backends(self):
        self.assertEqual(self._query(WinRMReadOnly, Reply(json.dumps(OS).encode()))['state'], 'ok')
        self.assertEqual(self._query(WinRMServicesReadOnly, Reply(json.dumps(SERVICES).encode()))['state'], 'ok')

    def test_ambiguous_duplicate_keys_rejected_by_both(self):
        for klass, body in ((WinRMReadOnly, b'{"os":{},"os":{},"disks":[]}'),
                            (WinRMServicesReadOnly, b'{"TotalCount":1,"TotalCount":2,"Services":[]}')):
            with self.subTest(klass=klass.__name__), self.assertRaisesRegex(WinRMError, 'winrm_invalid_response'):
                self._query(klass, Reply(body))

    def test_malformed_and_nonfinite_fail_closed(self):
        for klass in (WinRMReadOnly, WinRMServicesReadOnly):
            for payload in (b'{"value":NaN}', b'{"value":Infinity}', b'[]'*32769,
                            b'\xff', b'', 'not bytes', b'['*2000 + b'0' + b']'*2000):
                with self.subTest(klass=klass.__name__, payload=str(payload)[:20]):
                    with self.assertRaisesRegex(WinRMError, 'winrm_invalid_response'):
                        self._query(klass, Reply(payload))

    def test_untrusted_property_exceptions_are_redacted(self):
        for klass in (WinRMReadOnly, WinRMServicesReadOnly):
            with self.subTest(klass=klass.__name__):
                with self.assertRaises(WinRMError) as caught:
                    self._query(klass, ExplodingReply())
                self.assertEqual(str(caught.exception), 'winrm_invalid_response')
                self.assertIsNone(caught.exception.__cause__)

    def test_invalid_status_and_remote_failure(self):
        for klass in (WinRMReadOnly, WinRMServicesReadOnly):
            for status in (None, True, '0'):
                with self.subTest(klass=klass.__name__, status=status):
                    with self.assertRaisesRegex(WinRMError, 'winrm_invalid_response'):
                        self._query(klass, Reply(b'{}', status))
            with self.assertRaisesRegex(WinRMError, 'winrm_remote_query_failed'):
                self._query(klass, Reply(b'PRIVATE_PASSWORD_DO_NOT_LOG', 1))

    def test_offline_does_not_resolve_or_call_transport(self):
        for klass in (WinRMReadOnly, WinRMServicesReadOnly):
            calls = []
            client = klass(ORIGIN, 'operator', lambda: calls.append('secret'),
                           session_factory=lambda *_a, **_k: calls.append('network'))
            result = client.inventory() if klass is WinRMReadOnly else client.services()
            self.assertEqual(result['state'], 'offline')
            self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
