"""R95 service inventory tests: simulated transport, no remote execution."""
import json
import unittest
from winrm_readonly import WinRMError
from winrm_services_readonly import WinRMServicesReadOnly

ORIGIN = 'https://windows.example.test:5986'

class FakeSession:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []
        self.scripts = []
    def __call__(self, endpoint, username, password, *, timeout):
        self.calls.append((endpoint, username, password, timeout))
        return self
    def run_ps(self, script):
        self.scripts.append(script)
        return type('Reply', (), {'status_code': 0, 'std_out': self.reply})()

class ServicesTests(unittest.TestCase):
    def client(self, session, provider=lambda: 'SENSITIVE-PASSWORD'):
        return WinRMServicesReadOnly(ORIGIN, 'operator', provider, session_factory=session)

    def test_offline_has_no_side_effects(self):
        session = FakeSession(b'[]')
        self.assertEqual(self.client(session).services()['state'], 'offline')
        self.assertEqual(session.calls, [])

    def test_fixed_readonly_query_and_normalized_results(self):
        reply = json.dumps([{'Name':'Spooler','DisplayName':'Print Spooler',
                             'State':'Stopped','StartMode':'Manual'}]).encode()
        session = FakeSession(reply)
        result = self.client(session).services(online=True)
        self.assertEqual(result['services'][0]['name'], 'Spooler')
        self.assertEqual(result['limit'], 128)
        self.assertFalse(result['may_be_truncated'])
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0][0], ORIGIN + '/wsman')
        self.assertIn('Get-CimInstance -ClassName Win32_Service', session.scripts[0])
        self.assertNotIn('SENSITIVE-PASSWORD', session.scripts[0])
        self.assertNotIn('Start-Service', session.scripts[0])

    def test_cancelled_prevents_network(self):
        session = FakeSession(b'[]')
        with self.assertRaisesRegex(WinRMError, 'winrm_cancelled'):
            self.client(session).services(online=True, cancelled=lambda: True)
        self.assertEqual(session.calls, [])

    def test_invalid_response_is_rejected(self):
        for rows in ([{'Name':'A','DisplayName':'A','State':'Running','StartMode':'Auto'},
                      {'Name':'a','DisplayName':'B','State':'Stopped','StartMode':'Manual'}],
                     [{'Name':'A','DisplayName':'A','State':'Running\\nSECRET','StartMode':'Auto'}],
                     [{'Name':'A','DisplayName':'A','State':'Stopped','StartMode':'unexpected'}],
                     [{}], [None], [0] * 129):
            with self.subTest(rows=rows), self.assertRaisesRegex(WinRMError,'invalid_response'):
                self.client(FakeSession(json.dumps(rows).encode())).services(online=True)

    def test_transport_exception_redacted(self):
        class Exploding:
            def __call__(self, *args, **kwargs):
                raise RuntimeError('SENSITIVE-PASSWORD')
        with self.assertRaises(WinRMError) as cm:
            self.client(Exploding()).services(online=True)
        self.assertEqual(str(cm.exception), 'winrm_transport_unavailable')
        self.assertNotIn('SENSITIVE-PASSWORD', str(cm.exception))

    def test_bad_credentials_and_cancellation_type(self):
        session = FakeSession(b'[]')
        for provider in (None, lambda: None, lambda: '', lambda: 'bad\\x00pw'):
            with self.assertRaises(WinRMError):
                self.client(session, provider).services(online=True)
        with self.assertRaisesRegex(WinRMError, 'winrm_invalid_cancellation'):
            self.client(session).services(online=True, cancelled=1)
        self.assertEqual(session.calls, [])

    def test_empty_and_single_object(self):
        for value, count in (('[]',0), ('{"Name":"Spooler","DisplayName":"Printer","State":"Running","StartMode":"Auto"}',1)):
            result = self.client(FakeSession(value.encode())).services(online=True)
            self.assertEqual(len(result['services']),count)

if __name__ == '__main__': unittest.main()
