"""R99 WinCred contract: fail closed, no plaintext fallback or secret in errors."""
import unittest
from unittest.mock import patch
from winrm_readonly import WinRMError
from winrm_credential_ref import validate_winrm_credential_ref, resolve_winrm_credential


class WinRMCredentialReferenceR99Tests(unittest.TestCase):
    def test_strict_reference_allowlist(self):
        self.assertEqual(validate_winrm_credential_ref('wincred:OpenRemote/WinRM/srv-01'),
                         'OpenRemote/WinRM/srv-01')
        for value in (None, '', 'wincred:', 'vault:secret', 'wincred:../../secret',
                      'wincred:secret\nnext', 'wincred: secret', 'wincred:é',
                      'wincred:/absolute', 'wincred:' + 'x' * 129,
                      'wincred:target?secret=abc'):
            with self.subTest(value=repr(value)), self.assertRaises(WinRMError) as ctx:
                validate_winrm_credential_ref(value)
            self.assertEqual(str(ctx.exception), 'winrm_invalid_credential_reference')

    def test_resolution_calls_only_exact_target(self):
        calls = []
        self.assertEqual(resolve_winrm_credential('wincred:lab/winrm',
                         resolver=lambda target: calls.append(target) or 'ephemeral'), 'ephemeral')
        self.assertEqual(calls, ['lab/winrm'])

    def test_invalid_reference_does_not_call_resolver(self):
        calls = []
        with self.assertRaises(WinRMError):
            resolve_winrm_credential('wincred:bad\rvalue',
                                     resolver=lambda target: calls.append(target))
        self.assertEqual(calls, [])

    def test_provider_exception_is_sanitized(self):
        secret = 'SENSITIVE_PASSWORD_R99'
        def failing(_target):
            raise RuntimeError('provider failed: ' + secret)
        with self.assertRaises(WinRMError) as ctx:
            resolve_winrm_credential('wincred:lab', resolver=failing)
        self.assertEqual(str(ctx.exception), 'winrm_credentials_unavailable')
        self.assertIsNone(ctx.exception.__cause__)
        self.assertNotIn(secret, str(ctx.exception))

    def test_invalid_resolver_results_are_rejected(self):
        for value in ('', None, b'bytes', 'bad\x00secret'):
            with self.subTest(value=repr(value)), self.assertRaises(WinRMError) as ctx:
                resolve_winrm_credential('wincred:lab', resolver=lambda _: value)
            self.assertEqual(str(ctx.exception), 'winrm_credentials_unavailable')

    def test_default_resolver_uses_windows_credential_manager(self):
        with patch('windows_credentials.read_generic_password', return_value='test-only') as fn:
            self.assertEqual(resolve_winrm_credential('wincred:lab/target'), 'test-only')
            fn.assert_called_once_with('lab/target')


if __name__ == '__main__':
    unittest.main()
