"""SFTP home-directory transfer path regression tests.

Author: Abdelhalim Talbi.
"""
import unittest
from sftp_paths import remote_child


class SftpRelativePathTests(unittest.TestCase):
    def test_account_home_upload_download_target(self):
        self.assertEqual(remote_child('.', 'report.txt'), './report.txt')

    def test_relative_subdirectory(self):
        self.assertEqual(remote_child('./exports', 'report.txt'), 'exports/report.txt')

    def test_absolute_path_still_supported(self):
        self.assertEqual(remote_child('/srv/data', 'report.txt'), '/srv/data/report.txt')

    def test_reject_traversal_and_invalid_relative_path(self):
        for directory in ('../private', './..', 'foo/../private', 'foo//bar', '-danger', '', None, 'foo\\bar'):
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    remote_child(directory, 'report.txt')

    def test_reject_absolute_traversal_and_ambiguous_paths(self):
        for directory in ('/srv/../etc', '/srv//data', '/srv/./data', '/srv/data/', '/srv/\\\\data', '/srv/\x01data'):
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    remote_child(directory, 'report.txt')

    def test_root_directory_is_allowed(self):
        self.assertEqual(remote_child('/', 'report.txt'), '/report.txt')

    def test_reject_unsafe_filename(self):
        for filename in ('..', '../secret', 'a/b', 'a\\b', ''):
            with self.subTest(filename=filename):
                with self.assertRaises(ValueError):
                    remote_child('.', filename)


if __name__ == '__main__':
    unittest.main()
