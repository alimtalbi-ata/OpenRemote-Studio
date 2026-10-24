"""R90 consent lifecycle tests; no network or credentials."""
import unittest
from ssh_consent_guard import SSHConsentGuard


class ConsentGuardR90(unittest.TestCase):
    def test_offline_default_requires_explicit_approval(self):
        guard = SSHConsentGuard()
        self.assertFalse(guard.approved)
        guard.approve()
        self.assertTrue(guard.approved)

    def test_any_change_revokes_approval_even_if_reverted(self):
        guard = SSHConsentGuard()
        guard.approve()
        guard.configuration_changed()
        self.assertFalse(guard.approved)
        guard.configuration_changed()
        self.assertFalse(guard.approved)
        guard.approve()
        self.assertTrue(guard.approved)

    def test_revocation_and_retry_require_new_approval(self):
        guard = SSHConsentGuard()
        guard.approve()
        guard.revoke()
        self.assertFalse(guard.approved)
        guard.configuration_changed()
        self.assertFalse(guard.approved)
        guard.approve()
        self.assertTrue(guard.approved)

    def test_no_secret_fields_are_stored(self):
        guard = SSHConsentGuard()
        guard.approve()
        self.assertEqual(set(vars(guard)), {'_revision', '_approved_revision'})
        self.assertTrue(all(v is None or isinstance(v, int) for v in vars(guard).values()))


if __name__ == '__main__':
    unittest.main()
