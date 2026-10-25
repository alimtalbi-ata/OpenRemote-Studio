"""R93: opt-in read-only Windows inventory over verified HTTPS WinRM.

No network on import or offline calls. pywinrm is an OPTIONAL runtime dependency.
The only remote PowerShell script is a constant, without user interpolation.
Author: Abdelhalim Talbi.
"""
import os
import hashlib
import tempfile
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


@contextmanager
def _snapshot_ca_bundle(path, expected_digest):
    """Give pywinrm a private, immutable-for-this-request copy of pinned CA bytes.

    The original file is never handed to requests. The copy is removed on both
    success and transport failure; no snapshot is created in offline mode.
    """
    if path is None:
        yield None
        return
    data = _ca_bundle_bytes(path)
    if hashlib.sha256(data).digest() != expected_digest:
        raise WinRMError('winrm_ca_bundle_changed')
    try:
        with tempfile.TemporaryDirectory(prefix='ors-winrm-ca-') as directory:
            target = os.path.join(directory, 'trust.pem')
            flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, 'O_BINARY', 0))
            fd = os.open(target, flags, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
            if _ca_bundle_digest(target) != expected_digest:
                raise WinRMError('winrm_invalid_ca_bundle')
            yield target
    except (OSError, ValueError):
        raise WinRMError('winrm_invalid_ca_bundle') from None


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
        try:
            password = self._provider()
        except Exception:
            raise WinRMError('winrm_credentials_unavailable') from None
        if not isinstance(password, str) or not password or '\x00' in password:
            raise WinRMError('winrm_credentials_unavailable')
        if cancelled is not None and cancelled():
            raise WinRMError('winrm_cancelled')
        if self._ca_digest is not None and _ca_bundle_digest(self._ca_bundle) != self._ca_digest:
            raise WinRMError('winrm_ca_bundle_changed')
        try:
            with _snapshot_ca_bundle(self._ca_bundle, self._ca_digest) as ca_path:
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
