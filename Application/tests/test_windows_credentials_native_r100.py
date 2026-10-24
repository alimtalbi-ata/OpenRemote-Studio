"""R100: bounded WinCred reader + native Windows CredWrite/CredRead/CredDelete QA.

No production credentials, no network, no secrets in logs. A random, session-only
test credential is deleted in finally. Author: Abdelhalim Talbi.
"""
import ctypes
import secrets
import sys
import unittest
from ctypes import wintypes

from ssh_security import CredentialUnavailable
from windows_credentials import (_CREDENTIALW, _MAX_CREDENTIAL_BLOB_BYTES,
                                 read_generic_password)


class FakeAPI:
    def __init__(self, secret='safe'):
        self.secret = secret
        self.size_override = None
        self.kind_override = None
        self.freed = 0
        self.blob = None
        self.credential = _CREDENTIALW()

    def CredReadW(self, target, kind, flags, out):
        data = self.secret if isinstance(self.secret, bytes) else self.secret.encode('utf-16-le')
        self.blob = (ctypes.c_ubyte * max(1, len(data)))()
        for index, value in enumerate(data):
            self.blob[index] = value
        self.credential.Type = self.kind_override if self.kind_override is not None else 1
        self.credential.CredentialBlobSize = (self.size_override if self.size_override is not None
                                              else len(data))
        self.credential.CredentialBlob = ctypes.cast(self.blob, ctypes.POINTER(ctypes.c_ubyte))
        ctypes.cast(out, ctypes.POINTER(ctypes.POINTER(_CREDENTIALW)))[0] = ctypes.pointer(self.credential)
        return 1

    def CredFree(self, ptr):
        self.freed += 1


class WinCredBoundsR100(unittest.TestCase):
    def test_valid_unicode_and_native_free(self):
        api = FakeAPI('sëcret!')
        self.assertEqual(read_generic_password('test', api=api), 'sëcret!')
        self.assertEqual(api.freed, 1)

    def test_oversized_blob_rejected_before_read_and_freed(self):
        api = FakeAPI('safe')
        api.size_override = _MAX_CREDENTIAL_BLOB_BYTES + 2
        with self.assertRaises(CredentialUnavailable):
            read_generic_password('test', api=api)
        self.assertEqual(api.freed, 1)

    def test_wrong_credential_type_rejected_and_freed(self):
        api = FakeAPI('safe')
        api.kind_override = 2
        with self.assertRaises(CredentialUnavailable):
            read_generic_password('test', api=api)
        self.assertEqual(api.freed, 1)

    def test_embedded_nul_rejected_and_freed(self):
        api = FakeAPI('a\\x00b'.replace('\\x00', '\x00'))
        with self.assertRaises(CredentialUnavailable):
            read_generic_password('test', api=api)
        self.assertEqual(api.freed, 1)

    def test_invalid_utf16_rejected_and_freed(self):
        api = FakeAPI(bytes((0, 216)))
        with self.assertRaises(CredentialUnavailable):
            read_generic_password('test', api=api)
        self.assertEqual(api.freed, 1)

    def test_empty_and_odd_blob_rejected_and_freed(self):
        for value in ('', b'x'):
            with self.subTest(value=repr(value)):
                api = FakeAPI(value)
                with self.assertRaises(CredentialUnavailable):
                    read_generic_password('test', api=api)
                self.assertEqual(api.freed, 1)


@unittest.skipUnless(sys.platform == 'win32', 'requires native Windows Credential Manager')
class NativeWinCredR100(unittest.TestCase):
    def test_real_generic_credential_round_trip_and_delete(self):
        from winrm_credential_ref import resolve_winrm_credential
        api = ctypes.WinDLL('Advapi32', use_last_error=True)
        write = api.CredWriteW
        write.argtypes = [ctypes.POINTER(_CREDENTIALW), wintypes.DWORD]
        write.restype = wintypes.BOOL
        delete = api.CredDeleteW
        delete.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        delete.restype = wintypes.BOOL
        target = 'OpenRemoteStudio/R100QA/' + secrets.token_hex(16)
        secret = 'QA-' + secrets.token_hex(20)
        encoded = secret.encode('utf-16-le')
        blob = (ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
        cred = _CREDENTIALW()
        cred.Type = 1  # CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.UserName = 'OpenRemoteStudioQA'
        cred.Persist = 1  # CRED_PERSIST_SESSION; no durable credential
        cred.CredentialBlobSize = len(encoded)
        cred.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
        created = False
        try:
            self.assertTrue(write(ctypes.byref(cred), 0), 'native CredWriteW failed')
            created = True
            self.assertEqual(resolve_winrm_credential('wincred:' + target), secret)
        finally:
            if created:
                self.assertTrue(delete(target, 1, 0), 'native CredDeleteW cleanup failed')
        with self.assertRaises(CredentialUnavailable):
            read_generic_password(target)


if __name__ == '__main__':
    unittest.main()
