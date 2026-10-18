import unittest
from sftp_atomic_upload import upload_atomic
from sftp_atomic_transfer import TransferCancelled

class FakeSftp:
    def __init__(self, fail=False, after_put=None):
        self.files={'/data/file':b'old'};self.fail=fail;self.after_put=after_put;self.calls=[]
    def put(self, source, remote):
        self.calls.append(('put',remote));self.files[remote]=b'new'
        if self.after_put:self.after_put()
        if self.fail:raise OSError('network interrupted')
    def posix_rename(self, src, dst):
        self.calls.append(('publish',dst));self.files[dst]=self.files.pop(src)
    def remove(self, remote):
        self.calls.append(('remove',remote));self.files.pop(remote,None)

class AtomicUploadTests(unittest.TestCase):
    def test_success(self):
        s=FakeSftp();upload_atomic(s,'local','/data/file')
        self.assertEqual(s.files,{'/data/file':b'new'})
        self.assertEqual([x[0] for x in s.calls],['put','publish'])
    def test_network_failure_preserves_original(self):
        s=FakeSftp(fail=True)
        with self.assertRaises(OSError):upload_atomic(s,'local','/data/file')
        self.assertEqual(s.files,{'/data/file':b'old'})
        self.assertEqual([x[0] for x in s.calls],['put','remove'])
    def test_cancel_before_start(self):
        s=FakeSftp()
        with self.assertRaises(TransferCancelled):upload_atomic(s,'local','/data/file',lambda:True)
        self.assertEqual(s.calls,[])
    def test_cancel_after_put(self):
        flag=[False];s=FakeSftp(after_put=lambda:flag.__setitem__(0,True))
        with self.assertRaises(TransferCancelled):upload_atomic(s,'local','/data/file',lambda:flag[0])
        self.assertEqual(s.files,{'/data/file':b'old'})
    def test_unsupported_server_fails_closed(self):
        class Legacy:pass
        with self.assertRaisesRegex(RuntimeError,'POSIX atomic rename'):
            upload_atomic(Legacy(),'local','/data/file')
    def test_invalid_destination(self):
        with self.assertRaises(ValueError):upload_atomic(FakeSftp(),'local','/data/')
