"""R77 SSH identity/timeout fail-closed regressions (no network)."""
import math
import unittest
from ssh_transport import SSHSettings, create_ssh_client


class _NeverClient:
    def __init__(self):
        raise AssertionError('invalid settings reached client construction')


class SSHIdentityR77Tests(unittest.TestCase):
    def reject(self, **changes):
        options = dict(hostname='server.example', username='operator', port=22, timeout=15)
        options.update(changes)
        with self.assertRaises(ValueError):
            create_ssh_client(SSHSettings(**options), client_factory=_NeverClient)

    def test_reject_ambiguous_hostnames(self):
        for value in ('', ' host', 'host ', 'a b', 'a\nb', 'a\x00b',
                      'a\x7fb', 'a\u202eb', 'user@host', 'host/path',
                      'host\\path', None, 123):
            with self.subTest(host=repr(value)):
                self.reject(hostname=value)

    def test_reject_ambiguous_usernames(self):
        for value in ('', ' user', 'user ', 'user\nroot', 'user\x00root',
                      'user\u202eroot', None, 42):
            with self.subTest(username=repr(value)):
                self.reject(username=value)

    def test_reject_bad_ports(self):
        for value in (0, 65536, -1, True, False, 22.0, '22', None):
            with self.subTest(port=repr(value)):
                self.reject(port=value)

    def test_reject_non_finite_or_unbounded_timeouts(self):
        for value in (0, -1, math.inf, -math.inf, math.nan, True, False,
                      '5', None, 120.001):
            with self.subTest(timeout=repr(value)):
                self.reject(timeout=value)

    def test_allow_valid_ipv4_ipv6_and_unicode_hosts(self):
        for hostname in ('localhost', '127.0.0.1', '::1', 'srv.example', 'büro.example'):
            with self.subTest(hostname=hostname):
                SSHSettings(hostname, 'operator', timeout=120).validate()

    def test_allow_spaces_inside_username_but_not_controls(self):
        SSHSettings('server.example', 'service account').validate()


if __name__ == '__main__':
    unittest.main()
