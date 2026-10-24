"""R94: pywinrm timeout safety and read-only inventory validation. Author: Abdelhalim Talbi."""
import sys
import types
import unittest
from unittest.mock import patch

from winrm_readonly import WinRMReadOnly, WinRMError, _pywinrm_session


class WinRMTimeoutR94Tests(unittest.TestCase):
    def test_pywinrm_read_timeout_strictly_exceeds_operation_plus_ten(self):
        captured = []
        fake = types.SimpleNamespace(Session=lambda *a, **kw: captured.append((a, kw)) or object())
        with patch.dict(sys.modules, {'winrm': fake}):
            for timeout in (15, 16, 29, 30, 31, 60):
                _pywinrm_session('https://host.example.test:5986/wsman',
                                 'DOMAIN\\reader', 'synthetic', timeout=timeout)
        self.assertEqual(len(captured), 6)
        for (_, kw), timeout in zip(captured, (15, 16, 29, 30, 31, 60)):
            self.assertGreater(kw['read_timeout_sec'], kw['operation_timeout_sec'] + 10)
            self.assertEqual(kw['read_timeout_sec'], timeout)
            self.assertGreater(kw['operation_timeout_sec'], 0)
            self.assertLessEqual(kw['operation_timeout_sec'], 20)
            self.assertEqual(kw['server_cert_validation'], 'validate')
            self.assertEqual(kw['transport'], 'ntlm')

    def test_offline_requires_no_credentials_or_transport(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('offline invoked credential or transport')
        client = WinRMReadOnly('https://lab.example.test', 'reader',
                               credential_provider=forbidden, session_factory=forbidden)
        self.assertEqual(client.inventory()['state'], 'offline')


if __name__ == '__main__':
    unittest.main()
