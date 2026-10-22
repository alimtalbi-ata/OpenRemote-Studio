"""Unit tests for allowlisted SFTP UI messages; no Qt/network/Windows used.

Author: Abdelhalim Talbi.
"""
import unittest
from sftp_status import sftp_failure_text, sftp_journal_failure_text


class SftpSafeStatusTests(unittest.TestCase):
    def test_cancelled_is_distinct(self):
        self.assertIn('annulé', sftp_failure_text('InterruptedError'))

    def test_existing_remote_never_suggests_overwrite(self):
        self.assertIn('aucun écrasement', sftp_failure_text('FileExistsError'))

    def test_permission_error_is_actionable(self):
        self.assertIn('autorisations', sftp_failure_text('PermissionError'))

    def test_never_echoes_exception_details(self):
        marker = 'TEST_ONLY_SECRET_123'
        self.assertNotIn(marker, sftp_failure_text('OSError: ' + marker))
        self.assertNotIn(marker, sftp_failure_text(marker))

    def test_non_string_is_not_coerced(self):
        class Poison:
            def __str__(self):
                raise AssertionError('untrusted object stringified')
        self.assertIn('masqués', sftp_failure_text(Poison()))

    def test_audit_failures_are_generic(self):
        for stage in ('completed', 'cancel', 'stopped', 'error'):
            message = sftp_journal_failure_text(stage)
            self.assertNotIn('TEST_ONLY_SECRET_123', message)
            self.assertIn('journal', message.lower())

    def test_unknown_error_is_redacted(self):
        self.assertIn('masqués', sftp_failure_text('CustomSensitiveError'))


if __name__ == '__main__':
    unittest.main()
