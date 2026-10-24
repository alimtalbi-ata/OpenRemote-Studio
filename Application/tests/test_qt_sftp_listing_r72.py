"""Behavioral tests for SFTP directory completion guard.

These run without Qt or an SSH server. Author: Abdelhalim Talbi.
"""
import unittest
from sftp_listing_guard import should_display_listing


class SftpListingGuardTests(unittest.TestCase):
    def test_matching_path_displays(self):
        self.assertTrue(should_display_listing('/home/alice', '/home/alice'))
        self.assertTrue(should_display_listing('.', '.'))

    def test_stale_result_is_rejected(self):
        self.assertFalse(should_display_listing('/home/alice', '/home/bob'))
        self.assertFalse(should_display_listing('.', '..'))

    def test_invalid_paths_fail_closed(self):
        self.assertFalse(should_display_listing(None, '.'))
        self.assertFalse(should_display_listing('.', None))


if __name__ == '__main__':
    unittest.main()
