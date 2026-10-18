import errno
import unittest
from client_launch_diagnostics import launch_failure

class LaunchFailureTests(unittest.TestCase):
    def test_missing_client(self):
        self.assertEqual(launch_failure('SSH', FileNotFoundError('secret path'))['code'], 'client_missing')
    def test_access_denied(self):
        self.assertEqual(launch_failure('RDP', PermissionError('sensitive'))['code'], 'access_denied')
    def test_invalid_binary(self):
        self.assertEqual(launch_failure('VNC', OSError(errno.ENOEXEC, 'bad'))['code'], 'invalid_executable')
    def test_other_oserror(self):
        self.assertEqual(launch_failure('SFTP', OSError(errno.EIO, 'private'))['code'], 'process_error')
    def test_preflight(self):
        self.assertEqual(launch_failure('SSH', RuntimeError('password'))['code'], 'preflight_rejected')
    def test_no_sensitive_exception_text(self):
        for error in (FileNotFoundError('password=TOPSECRET'), RuntimeError('password=TOPSECRET')):
            self.assertNotIn('TOPSECRET',launch_failure('SSH',error)['message'])
    def test_no_remote_claim(self):
        self.assertFalse(launch_failure('SSH',FileNotFoundError())['remote_status_verified'])
    def test_invalid_exception(self):
        with self.assertRaises(TypeError):launch_failure('SSH',Exception('bad'))
