import ctypes
import sys
import unittest
from unittest.mock import patch
from ssh_security import CredentialUnavailable
from windows_credentials import read_generic_password, _CREDENTIALW

class FakeAPI:
    def __init__(self, password=None):
        self.password = password
        self.freed = 0
        self.credential = _CREDENTIALW()
        self.blob = None
    def CredReadW(self, target, kind, flags, out):
        if self.password is None: return 0
        data = self.password.encode('utf-16-le')
        self.blob = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        self.credential.CredentialBlobSize = len(data)
        self.credential.CredentialBlob = ctypes.cast(self.blob, ctypes.POINTER(ctypes.c_ubyte))
        p = ctypes.cast(out, ctypes.POINTER(ctypes.POINTER(_CREDENTIALW)))
        p[0] = ctypes.pointer(self.credential)
        return 1
    def CredFree(self, ptr): self.freed += 1

class WindowsCredentialTests(unittest.TestCase):
    def test_success(self):
        api=FakeAPI('sëcret!')
        self.assertEqual(read_generic_password('OpenRemote:test',api=api),'sëcret!')
        self.assertEqual(api.freed,1)
    def test_missing_fails_closed(self):
        api=FakeAPI()
        with self.assertRaises(CredentialUnavailable): read_generic_password('missing',api=api)
        self.assertEqual(api.freed,0)
    def test_empty_rejected_and_freed(self):
        api=FakeAPI('')
        with self.assertRaises(CredentialUnavailable): read_generic_password('empty',api=api)
        self.assertEqual(api.freed,1)
    def test_invalid_target(self):
        with self.assertRaises(ValueError): read_generic_password('  ',api=FakeAPI('x'))
    def test_non_windows_unavailable(self):
        with patch.object(sys,'platform','linux'):
            with self.assertRaises(CredentialUnavailable): read_generic_password('x')
if __name__=='__main__': unittest.main()
