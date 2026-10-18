
import tempfile
import unittest
from pathlib import Path
from sftp_paths import remote_child,local_entries
class SftpPathsTests(unittest.TestCase):
    def test_remote_path(self):
        self.assertEqual(remote_child('/data/','test.txt'),'/data/test.txt')
    def test_parent_rejected(self):
        with self.assertRaises(ValueError):remote_child('/data','..')
    def test_slash_rejected(self):
        with self.assertRaises(ValueError):remote_child('/data','../../etc/passwd')
    def test_absolute_required(self):
        with self.assertRaises(ValueError):remote_child('data','file')
    def test_local_directory_sorted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'z.txt').write_text('z');(root/'a').mkdir()
            self.assertEqual(local_entries(root),[('a',True),('z.txt',False)])
    def test_local_missing(self):
        with self.assertRaises(ValueError):local_entries('/not-a-real-openremote-folder-12345')
