"""V28.5: cleanup is restricted to the transfer-owned temporary file."""
import unittest
from unittest.mock import patch
from sftp_atomic_upload import upload_atomic
from sftp_atomic_transfer import TransferCancelled

class Remote:
    def __init__(self, fail_put=False, fail_remove=False, fail_rename=False):
        self.fail_put=fail_put; self.fail_remove=fail_remove; self.fail_rename=fail_rename
        self.files={"/data/file":b"old", "/data/.file.other.partial":b"another session"}
        self.removed=[]; self.staged=None
    def put(self, source, target):
        self.staged=target; self.files[target]=b"new"
        if self.fail_put: raise OSError("put failed")
    def posix_rename(self, source, target):
        if self.fail_rename: raise OSError("rename failed")
        self.files[target]=self.files.pop(source)
    def remove(self, target):
        self.removed.append(target)
        if self.fail_remove: raise OSError("cleanup denied")
        self.files.pop(target,None)

class OwnedCleanupTests(unittest.TestCase):
    def test_failed_put_only_removes_owned_path(self):
        s=Remote(fail_put=True)
        with self.assertRaisesRegex(OSError,"put failed"):
            upload_atomic(s,"local","/data/file")
        self.assertEqual(s.removed,[s.staged])
        self.assertEqual(s.files["/data/file"],b"old")
        self.assertEqual(s.files["/data/.file.other.partial"],b"another session")
    def test_cleanup_failure_is_reported_even_when_put_fails(self):
        s=Remote(fail_put=True,fail_remove=True)
        with self.assertRaisesRegex(OSError,"put failed") as ctx:
            upload_atomic(s,"local","/data/file")
        self.assertTrue(any("cleanup failed" in note for note in ctx.exception.__notes__))
        self.assertEqual(s.removed,[s.staged])
    def test_failed_publication_never_removes_other_session_file(self):
        s=Remote(fail_rename=True)
        with self.assertRaisesRegex(OSError,"rename failed"):
            upload_atomic(s,"local","/data/file")
        self.assertEqual(s.removed,[s.staged])
        self.assertEqual(s.files["/data/file"],b"old")
        self.assertEqual(s.files["/data/.file.other.partial"],b"another session")
