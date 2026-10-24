"""Behavioral regression for Qt SFTP parent navigation.

Author: Abdelhalim Talbi.
"""
import unittest
from sftp_paths import remote_navigate


class SftpNavigationTests(unittest.TestCase):
    def test_home_parent_stays_at_home(self):
        self.assertEqual(remote_navigate('.', '../'), '.')

    def test_relative_child_and_parent(self):
        self.assertEqual(remote_navigate('.', 'exports/'), './exports')
        self.assertEqual(remote_navigate('./exports', '../'), '.')

    def test_absolute_child_and_parent(self):
        self.assertEqual(remote_navigate('/srv/data', 'logs/'), '/srv/data/logs')
        self.assertEqual(remote_navigate('/srv/data', '../'), '/srv')
        self.assertEqual(remote_navigate('/', '../'), '/')

    def test_parent_navigation_rejects_unsafe_source_path(self):
        for directory in ('/srv/../private', '/srv//private', '/srv/./private', 'foo/../bar', 'foo//bar'):
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    remote_navigate(directory, '../')

    def test_invalid_entries_rejected(self):
        for entry in ('../secret/', 'bad\\name/', 'bad\nname/', 'file.txt', './'):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    remote_navigate('.', entry)


if __name__ == '__main__':
    unittest.main()
