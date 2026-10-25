"""R103 P1: external WinRM errors must not leak provider secret strings.
Real application backends, hostile in-memory transports; NO real WinRM server.
Author: Abdelhalim Talbi.
"""
import unittest
from winrm_readonly import WinRMReadOnly, WinRMError
from winrm_services_readonly import WinRMServicesReadOnly
from winrm_response import decode_winrm_json

ORIGIN = 'https://windows.example.test:5986'
SECRET = 'R103_SECRET_NEVER_EXPOSE'

class HostileResponse:
    def __init__(self, prop, exception):
        self.prop, self.exception = prop, exception
    @property
    def status_code(self):
        if self.prop == 'status_code':
            raise self.exception
        return 0
    @property
    def std_out(self):
        if self.prop == 'std_out':
            raise self.exception
        return b'{}'

class HostileSession:
    def __init__(self, exception, phase):
        self.exception, self.phase = exception, phase
    def __call__(self, *_args, **_kwargs):
        if self.phase == 'construct':
            raise self.exception
        return self
    def run_ps(self, _script):
        raise self.exception

class WinRMExceptionBoundaryR103Tests(unittest.TestCase):
    def assert_redacted(self, call, expected):
        with self.assertRaises(WinRMError) as caught:
            call()
        self.assertEqual(str(caught.exception), expected)
        self.assertNotIn(SECRET, repr(caught.exception))
        self.assertIsNone(caught.exception.__cause__)

    def test_response_properties_redact_even_winrm_errors(self):
        for prop in ('status_code', 'std_out'):
            for exc in (RuntimeError(SECRET), WinRMError(SECRET)):
                with self.subTest(prop=prop, exception=type(exc).__name__):
                    self.assert_redacted(
                        lambda: decode_winrm_json(HostileResponse(prop, exc)),
                        'winrm_invalid_response')

    def test_factory_and_run_ps_errors_redacted_in_both_backends(self):
        for backend, method in ((WinRMReadOnly, 'inventory'),
                                (WinRMServicesReadOnly, 'services')):
            for phase in ('construct', 'run_ps'):
                for exc in (RuntimeError(SECRET), WinRMError(SECRET)):
                    with self.subTest(backend=backend.__name__, phase=phase,
                                      exception=type(exc).__name__):
                        client = backend(ORIGIN, 'operator', lambda: SECRET,
                                         session_factory=HostileSession(exc, phase))
                        self.assert_redacted(lambda: getattr(client, method)(online=True),
                                             'winrm_transport_unavailable')

    def test_remote_failure_never_reads_payload_or_stderr(self):
        class Failed:
            status_code = 1
            @property
            def std_out(self):
                raise AssertionError('must not read failed stdout')
            @property
            def std_err(self):
                raise AssertionError('must never read stderr')
        self.assert_redacted(lambda: decode_winrm_json(Failed()),
                             'winrm_remote_query_failed')

    def test_offline_never_uses_provider_or_transport(self):
        for backend, method in ((WinRMReadOnly, 'inventory'),
                                (WinRMServicesReadOnly, 'services')):
            def forbidden(*_args, **_kwargs):
                raise AssertionError('offline contacted transport')
            client = backend(ORIGIN, 'operator', forbidden, session_factory=forbidden)
            self.assertEqual(getattr(client, method)()['state'], 'offline')

if __name__ == '__main__':
    unittest.main()
