"""Read Windows Credential Manager generic credentials without persisting secrets.

Only generic credentials (CRED_TYPE_GENERIC) are supported. This module never
creates or logs credentials. The credential target is supplied by the caller.
"""
import ctypes
import sys
from ctypes import wintypes
from ssh_security import CredentialUnavailable

CRED_TYPE_GENERIC = 1

class _CREDENTIALW(ctypes.Structure):
    _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)),
                ('Persist', wintypes.DWORD), ('AttributeCount', wintypes.DWORD),
                ('Attributes', ctypes.c_void_p), ('TargetAlias', wintypes.LPWSTR),
                ('UserName', wintypes.LPWSTR)]


def read_generic_password(target: str, *, api=None) -> str:
    """Retrieve UTF-16LE generic credential secret, raising closed on failure.

    `api` allows testing without Windows; production uses advapi32 CredReadW.
    """
    if not isinstance(target, str) or not target.strip():
        raise ValueError('credential target must be nonempty')
    if api is None:
        if sys.platform != 'win32':
            raise CredentialUnavailable('Windows Credential Manager requires Windows')
        api = ctypes.WinDLL('Advapi32', use_last_error=True)
    credptr = ctypes.POINTER(_CREDENTIALW)()
    read = api.CredReadW
    if hasattr(read, 'argtypes'):
        read.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                         ctypes.POINTER(ctypes.POINTER(_CREDENTIALW))]
        read.restype = wintypes.BOOL
    free = api.CredFree
    if hasattr(free, 'argtypes'):
        free.argtypes = [ctypes.c_void_p]
        free.restype = None
    if not read(target, CRED_TYPE_GENERIC, 0, ctypes.byref(credptr)):
        raise CredentialUnavailable('Windows credential not found or inaccessible')
    try:
        credential = credptr.contents
        size = credential.CredentialBlobSize
        if not size or size % 2 or not credential.CredentialBlob:
            raise CredentialUnavailable('invalid Windows credential secret')
        secret = ctypes.string_at(credential.CredentialBlob, size).decode('utf-16-le')
        if not secret:
            raise CredentialUnavailable('empty Windows credential secret')
        return secret
    except UnicodeDecodeError as exc:
        raise CredentialUnavailable('credential secret is not UTF-16LE') from exc
    finally:
        free(ctypes.cast(credptr, ctypes.c_void_p))


def windows_credential_provider(target: str) -> str:
    """Callable provider for SSH credential_ref (generic credential target)."""
    return read_generic_password(target)
