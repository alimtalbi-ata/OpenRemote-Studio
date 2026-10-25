"""R93: opt-in read-only Windows inventory over verified HTTPS WinRM.

No network on import or offline calls. pywinrm is an OPTIONAL runtime dependency.
The only remote PowerShell script is a constant, without user interpolation.
Author: Abdelhalim Talbi.
"""
import os
import hashlib
import tempfile
import secrets
import shutil
from contextlib import contextmanager
import re
import ssl
import stat
import unicodedata
from urllib.parse import urlsplit


class WinRMError(RuntimeError):
    """Fixed error codes only; never chain sensitive provider/transport exceptions."""


# Constant allowlisted, read-only CIM queries. Never accept arbitrary scripts.
_INVENTORY_PS = r'''
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance -ClassName Win32_OperatingSystem |
  Select-Object Caption, Version, BuildNumber, CSName
$disks = @(Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType=3' |
  Select-Object DeviceID, Size, FreeSpace)
@{ os = $os; disks = $disks } | ConvertTo-Json -Compress -Depth 4
'''.strip()
_HOST = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$')
_DRIVE = re.compile(r'^[A-Za-z]:$')


def _endpoint(origin):
    if not isinstance(origin, str) or not origin or any(ord(c) < 33 or ord(c) == 127 for c in origin):
        raise WinRMError('winrm_invalid_https_origin')
    try:
        parts = urlsplit(origin)
        port = parts.port
    except ValueError:
        raise WinRMError('winrm_invalid_https_origin') from None
    host = parts.hostname
    if (parts.scheme != 'https' or not host or not _HOST.fullmatch(host)
            or parts.username is not None or parts.password is not None
            or parts.path not in ('', '/') or parts.query or parts.fragment
            or '\\' in origin or '%' in origin or '..' in host
            or (port is not None and not 1 <= port <= 65535)):
        raise WinRMError('winrm_invalid_https_origin')
    return f'https://{host.lower()}:{port or 5986}/wsman'


def _text(value, maximum=160):
    if not isinstance(value, str):
        raise WinRMError('winrm_invalid_response')
    # Remote CIM fields are untrusted display data. Invisible formatting,
    # bidi overrides, surrogate code points and line separators can spoof
    # Qt rows even when ordinary ASCII control characters are absent.
    if (len(value) > maximum or any(
            unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp')
            or 0xFDD0 <= ord(c) <= 0xFDEF
            or (ord(c) & 0xFFFE) == 0xFFFE
            for c in value)):
        raise WinRMError('winrm_invalid_response')
    return value


def _size(value):
    if type(value) is int:
        number = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 20:
        number = int(value)
    else:
        raise WinRMError('winrm_invalid_response')
    if not 0 <= number <= 2**64 - 1:
        raise WinRMError('winrm_invalid_response')
    return number


def _inventory(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('os'), dict):
        raise WinRMError('winrm_invalid_response')
    os_data = raw['os']
    os_info = {
        'caption': _text(os_data.get('Caption')),
        'version': _text(os_data.get('Version'), 64),
        'build': _text(os_data.get('BuildNumber'), 32),
        'computer': _text(os_data.get('CSName'), 253),
    }
    disks = raw.get('disks')
    if disks is None:
        disks = []
    if isinstance(disks, dict):
        disks = [disks]
    if not isinstance(disks, list) or len(disks) > 128:
        raise WinRMError('winrm_invalid_response')
    normalized = []
    seen = set()
    for item in disks:
        if not isinstance(item, dict):
            raise WinRMError('winrm_invalid_response')
        drive = _text(item.get('DeviceID'), 2)
        if not _DRIVE.fullmatch(drive) or drive in seen:
            raise WinRMError('winrm_invalid_response')
        seen.add(drive)
        size, free = _size(item.get('Size')), _size(item.get('FreeSpace'))
        if free > size:
            raise WinRMError('winrm_invalid_response')
        normalized.append({'drive': drive, 'size_bytes': size, 'free_bytes': free})
    return {'state': 'ok', 'read_only': True, 'os': os_info, 'disks': normalized}


def validate_ca_bundle(path):
    """Fail-closed validation of optional local PEM trust; no TLS bypass."""
    if path is None or path == '':
        return None
    if (not isinstance(path, str) or len(path) > 1024
            or not os.path.isabs(path) or path.startswith(('\\\\', '//'))
            or any(ord(c) < 32 or ord(c) == 127 for c in path)):
        raise WinRMError('winrm_invalid_ca_bundle')
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 1048576:
            raise ValueError('not a bounded regular file')
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cafile=path)
    except (OSError, ValueError, ssl.SSLError):
        raise WinRMError('winrm_invalid_ca_bundle') from None
    return path


def _ca_bundle_bytes(path):
    """Pin the validated CA bytes, not just its pathname, before reading secrets.

    Read through a regular-file descriptor; reject symlink swaps and changes
    between lstat and open. The PEM contains public certificates, not secrets.
    """
    try:
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 1048576:
            raise ValueError('invalid CA file')
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags)
        try:
            actual = os.fstat(fd)
            if (not stat.S_ISREG(actual.st_mode) or not 0 < actual.st_size <= 1048576
                    or (before.st_dev, before.st_ino) != (actual.st_dev, actual.st_ino)):
                raise ValueError('CA changed during open')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                data = stream.read(1048577)
            after = os.fstat(fd)
            if (not 0 < len(data) <= 1048576 or len(data) != actual.st_size
                    or (actual.st_size, actual.st_mtime_ns, actual.st_ctime_ns)
                    != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
                raise ValueError('CA changed during read')
        finally:
            os.close(fd)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cadata=data.decode('ascii'))
        return data
    except (OSError, ValueError, UnicodeError, ssl.SSLError):
        raise WinRMError('winrm_invalid_ca_bundle') from None


def _ca_bundle_digest(path):
    """Digest of a safely opened and validated public CA PEM."""
    return hashlib.sha256(_ca_bundle_bytes(path)).digest()


def _parse_sddl_flags(value, allowed):
    """Parse concatenated SDDL flags without accepting unknown suffixes."""
    tokens = []
    remaining = value
    while remaining:
        token = next((item for item in allowed if remaining.startswith(item)), None)
        if token is None:
            return None
        tokens.append(token)
        remaining = remaining[len(token):]
    return set(tokens)


def _windows_current_user_sid():
    """Return the current process user SID using the token API."""
    import ctypes
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

    class TOKEN_USER(ctypes.Structure):
        _fields_ = [("User", SID_AND_ATTRIBUTES)]

    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    advapi.OpenProcessToken.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
    ]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD)
    ]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)
    ]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p

    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008,
                                   ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        required = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
        if not 1 <= required.value <= 65536:
            raise OSError("invalid token information size")
        buffer = ctypes.create_string_buffer(required.value)
        if not advapi.GetTokenInformation(
                token, 1, ctypes.cast(buffer, wintypes.LPVOID),
                required.value, ctypes.byref(required)):
            raise ctypes.WinError(ctypes.get_last_error())
        sid_pointer = ctypes.cast(
            buffer, ctypes.POINTER(TOKEN_USER)
        ).contents.User.Sid
        sid_text = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid_pointer, ctypes.byref(sid_text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            sid = sid_text.value or ""
        finally:
            kernel.LocalFree(ctypes.cast(sid_text, ctypes.c_void_p))
    finally:
        kernel.CloseHandle(token)
    if not re.fullmatch(r"S-1-(?:\d+-){1,15}\d+", sid, flags=re.ASCII):
        raise OSError("invalid process user SID")
    return sid


def _read_windows_dacl_sddl(path):
    """Read only the DACL SDDL; caller rejects anything broader than expected."""
    import ctypes
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p)
    ]
    advapi.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)
    ]
    advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p

    dacl = ctypes.c_void_p()
    descriptor = ctypes.c_void_p()
    status = advapi.GetNamedSecurityInfoW(
        path, 1, 0x00000004, None, None, ctypes.byref(dacl), None,
        ctypes.byref(descriptor)
    )
    if status != 0:
        raise OSError(status, "DACL inspection failed")
    string_pointer = wintypes.LPWSTR()
    string_length = wintypes.DWORD()
    try:
        if not advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor, 1, 0x00000004, ctypes.byref(string_pointer),
                ctypes.byref(string_length)):
            raise ctypes.WinError(ctypes.get_last_error())
        return string_pointer.value or ""
    finally:
        if string_pointer:
            kernel.LocalFree(ctypes.cast(string_pointer, ctypes.c_void_p))
        if descriptor:
            kernel.LocalFree(descriptor)


def _sddl_is_private(sddl, user_sid, *, directory):
    """Pure fail-closed check of the required two-principal snapshot DACL."""
    match = re.fullmatch(r"D:([A-Z]*)(.*)", sddl)
    if not match:
        return False
    control_flags = _parse_sddl_flags(match.group(1), ("AI", "AR", "P"))
    if control_flags is None or (directory and "P" not in control_flags):
        return False
    ace_text = match.group(2)
    aces = re.findall(r"\(([^()]*)\)", ace_text)
    if len(aces) != 2 or "".join("(" + ace + ")" for ace in aces) != ace_text:
        return False
    expected_sids = {user_sid.upper(), "SY", "S-1-5-18"}
    found_sids = set()
    for ace in aces:
        parts = ace.split(";")
        if len(parts) != 6 or parts[0] != "A":
            return False
        flags = _parse_sddl_flags(
            parts[1], ("OI", "CI", "NP", "IO", "ID", "SA", "FA")
        )
        if flags is None or parts[2].lower() not in {"fa", "0x1f01ff"}:
            return False
        if parts[3] or parts[4]:
            return False
        principal = parts[5].upper()
        if principal not in expected_sids:
            return False
        if directory:
            if flags != {"OI", "CI"}:
                return False
        elif flags != {"ID"}:
            return False
        found_sids.add(principal)
    return found_sids == {user_sid.upper(), "SY"} or found_sids == {
        user_sid.upper(), "S-1-5-18"
    }


def _windows_dacl_is_private(path, user_sid, *, directory):
    """Read and validate a Windows DACL; inspection errors are never permissive."""
    try:
        return _sddl_is_private(
            _read_windows_dacl_sddl(path), user_sid, directory=directory
        )
    except Exception:
        # Native ACL inspection is a security boundary: any unexpected
        # inspection failure must be interpreted as an unsafe DACL.
        return False


def _create_windows_private_directory():
    """Create a local temp directory with an explicit, protected two-principal DACL."""
    import ctypes
    from ctypes import wintypes

    base = os.path.abspath(tempfile.gettempdir())
    drive, _ = os.path.splitdrive(base)
    is_junction = getattr(os.path, "isjunction", None)
    if (not drive or not os.path.isabs(base) or base.startswith(("\\\\", "//"))
            or not os.path.isdir(base) or os.path.islink(base)
            or (is_junction is not None and is_junction(base))):
        raise OSError("unsafe Windows temporary directory")

    user_sid = _windows_current_user_sid()
    sddl = "D:P(A;OICI;FA;;;" + user_sid + ")(A;OICI;FA;;;SY)"
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.DWORD)
    ]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    kernel.CreateDirectoryW.argtypes = [
        wintypes.LPCWSTR, ctypes.c_void_p
    ]
    kernel.CreateDirectoryW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", wintypes.BOOL)
        ]

    descriptor = ctypes.c_void_p()
    descriptor_size = wintypes.DWORD()
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), ctypes.byref(descriptor_size)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes = SECURITY_ATTRIBUTES(
            ctypes.sizeof(SECURITY_ATTRIBUTES), descriptor, False
        )
        for _ in range(3):
            path = os.path.join(base, "ors-winrm-ca-" + secrets.token_hex(16))
            if kernel.CreateDirectoryW(path, ctypes.byref(attributes)):
                if _windows_dacl_is_private(path, user_sid, directory=True):
                    return path, user_sid
                try:
                    os.rmdir(path)
                except OSError:
                    pass
                raise OSError("Windows temporary directory ACL verification failed")
            error = ctypes.get_last_error()
            if error != 183:
                raise ctypes.WinError(error)
        raise OSError("could not allocate a unique Windows temporary directory")
    finally:
        kernel.LocalFree(descriptor)


@contextmanager
def _private_snapshot_directory():
    """Yield a per-request directory whose ACL is enforced before any secret read."""
    if os.name != "nt":
        with tempfile.TemporaryDirectory(prefix="ors-winrm-ca-") as directory:
            yield directory, None
        return
    try:
        directory, user_sid = _create_windows_private_directory()
    except Exception:
        # Keep WinAPI errors and local paths out of UI/log messages. Any ACL
        # setup error blocks the credential provider and network request.
        raise WinRMError("winrm_snapshot_acl_failed") from None
    try:
        yield directory, user_sid
    finally:
        try:
            shutil.rmtree(directory)
        except FileNotFoundError:
            if os.path.lexists(directory):
                raise WinRMError("winrm_snapshot_cleanup_failed") from None
        except OSError:
            raise WinRMError("winrm_snapshot_cleanup_failed") from None


@contextmanager
def _snapshot_ca_bundle(path, expected_digest):
    """Give pywinrm a pinned PEM snapshot with restrictive ACLs and bounded lifetime."""
    if path is None:
        yield None
        return
    data = _ca_bundle_bytes(path)
    if hashlib.sha256(data).digest() != expected_digest:
        raise WinRMError("winrm_ca_bundle_changed")
    try:
        with _private_snapshot_directory() as (directory, user_sid):
            target = os.path.join(directory, "trust.pem")
            flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, "O_BINARY", 0))
            fd = os.open(target, flags, 0o600)
            try:
                if user_sid is not None and not _windows_dacl_is_private(
                        target, user_sid, directory=False):
                    raise WinRMError("winrm_snapshot_acl_failed")
                stream = os.fdopen(fd, "wb")
                fd = None
                with stream:
                    stream.write(data)
            finally:
                if fd is not None:
                    os.close(fd)
            if (_ca_bundle_digest(target) != expected_digest
                    or (user_sid is not None and not _windows_dacl_is_private(
                        target, user_sid, directory=False))):
                raise WinRMError("winrm_snapshot_acl_failed"
                                 if user_sid is not None
                                 else "winrm_invalid_ca_bundle")
            yield target
    except (OSError, ValueError):
        raise WinRMError("winrm_invalid_ca_bundle") from None


def _pywinrm_session(endpoint, username, password, *, timeout, ca_bundle=None):
    try:
        import winrm
    except ImportError:
        raise WinRMError('winrm_dependency_missing') from None
    # pywinrm uses requests with CA validation; no HTTP or certificate bypass.
    kwargs = {'ca_trust_path': ca_bundle} if ca_bundle is not None else {}
    return winrm.Session(endpoint, auth=(username, password), transport='ntlm',
                         server_cert_validation='validate',
                         **kwargs,
                         # pywinrm requires read_timeout_sec > operation_timeout_sec + 10.
                         # R93 used equality at 15/30s and failed before sending a request.
                         operation_timeout_sec=min(20, timeout - 11),
                         read_timeout_sec=timeout)


class WinRMReadOnly:
    """No connection without online=True and a runtime credential callback."""

    def __init__(self, origin, username, credential_provider=None, *, session_factory=None,
                 timeout=30, ca_bundle=None):
        self._endpoint = _endpoint(origin)
        self._ca_bundle = validate_ca_bundle(ca_bundle)
        self._ca_digest = (_ca_bundle_digest(self._ca_bundle)
                           if self._ca_bundle is not None else None)
        if (not isinstance(username, str) or not username or len(username) > 256
                or any(ord(c) < 33 or ord(c) == 127 for c in username)):
            raise WinRMError('winrm_invalid_username')
        if type(timeout) is not int or not 15 <= timeout <= 60:
            raise WinRMError('winrm_invalid_timeout')
        self._username = username
        self._provider = credential_provider
        self._factory = session_factory or _pywinrm_session
        self._timeout = timeout

    def __repr__(self):
        return '<WinRMReadOnly redacted>'

    def inventory(self, *, online=False, cancelled=None):
        if not online:
            return {'state': 'offline', 'read_only': True, 'os': None, 'disks': []}
        if cancelled is not None and not callable(cancelled):
            raise WinRMError('winrm_invalid_cancellation')
        if cancelled is not None and cancelled():
            raise WinRMError('winrm_cancelled')
        if self._ca_digest is not None and _ca_bundle_digest(self._ca_bundle) != self._ca_digest:
            raise WinRMError('winrm_ca_bundle_changed')
        if not callable(self._provider):
            raise WinRMError('winrm_credentials_required')
        password = None
        try:
            # Establish and verify the per-request trust file before resolving
            # any credential; ACL failure must fail closed without reading it.
            with _snapshot_ca_bundle(self._ca_bundle, self._ca_digest) as ca_path:
                if cancelled is not None and cancelled():
                    raise WinRMError('winrm_cancelled')
                try:
                    password = self._provider()
                except Exception:
                    raise WinRMError('winrm_credentials_unavailable') from None
                if not isinstance(password, str) or not password or '\x00' in password:
                    raise WinRMError('winrm_credentials_unavailable')
                if cancelled is not None and cancelled():
                    raise WinRMError('winrm_cancelled')
                try:
                    kwargs = {'ca_bundle': ca_path} if ca_path is not None else {}
                    session = self._factory(self._endpoint, self._username, password,
                                            timeout=self._timeout, **kwargs)
                    response = session.run_ps(_INVENTORY_PS)
                # Untrusted transport errors must never expose passwords or paths.
                except Exception:
                    raise WinRMError('winrm_transport_unavailable') from None
        finally:
            password = None
        if cancelled is not None and cancelled():
            raise WinRMError('winrm_cancelled')
        from winrm_response import decode_winrm_json
        return _inventory(decode_winrm_json(response))