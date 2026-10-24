"""R99: explicit Windows Credential Manager reference for read-only WinRM.

Only local Generic Credentials are supported. No secret is stored, exported or
resolved until the operator explicitly authorizes a WinRM read. No fallback to
plaintext or remote vault endpoints. Author: Abdelhalim Talbi.
"""
import re

from winrm_readonly import WinRMError

_TARGET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@:-]{0,127}\\Z", re.ASCII)


def validate_winrm_credential_ref(reference):
    """Return a validated WinCred target; reject ambiguous/unbounded references."""
    if not isinstance(reference, str) or not reference.startswith('wincred:'):
        raise WinRMError('winrm_invalid_credential_reference')
    target = reference[len('wincred:'):]
    if not _TARGET.fullmatch(target) or '..' in target:
        raise WinRMError('winrm_invalid_credential_reference')
    return target


def resolve_winrm_credential(reference, *, resolver=None):
    """Resolve at execution time only, fail closed and never leak provider errors."""
    target = validate_winrm_credential_ref(reference)
    if resolver is None:
        from windows_credentials import read_generic_password
        resolver = read_generic_password
    if not callable(resolver):
        raise WinRMError('winrm_credentials_unavailable')
    try:
        password = resolver(target)
    except Exception:
        raise WinRMError('winrm_credentials_unavailable') from None
    if not isinstance(password, str) or not password or '\x00' in password:
        raise WinRMError('winrm_credentials_unavailable')
    return password
