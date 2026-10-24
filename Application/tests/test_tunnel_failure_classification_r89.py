"""R89: typed SSH error classification never exposes exception text."""
import unittest
from tunnel_controller import _safe_ssh_failure_code, TunnelSnapshot


class SSHFailureClassificationR89(unittest.TestCase):
    def test_generic_exception_text_is_never_used(self):
        error = RuntimeError('SECRET=do-not-log host=private.internal')
        self.assertEqual(_safe_ssh_failure_code(error), 'generic')
        self.assertNotIn('SECRET', str(TunnelSnapshot(
            'failed', failure_code=_safe_ssh_failure_code(error))))

    def test_host_key_error_is_typed(self):
        try:
            from paramiko.ssh_exception import BadHostKeyException
        except ImportError:
            self.skipTest('Paramiko not installed')
        self.assertEqual(_safe_ssh_failure_code(
            BadHostKeyException('sensitive.example', None, None)), 'host_key')

    def test_authentication_error_is_typed(self):
        try:
            from paramiko.ssh_exception import AuthenticationException
        except ImportError:
            self.skipTest('Paramiko not installed')
        self.assertEqual(_safe_ssh_failure_code(
            AuthenticationException('user secret rejected')), 'authentication')


if __name__ == '__main__':
    unittest.main()
