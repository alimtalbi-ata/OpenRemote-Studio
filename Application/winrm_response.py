"""R102: strict bounded WinRM response decoder, shared by fixed read-only queries.

Provider errors and raw payloads are never included in public exceptions.
Author: Abdelhalim Talbi.
"""
import json

from winrm_readonly import WinRMError


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError('non-finite JSON number')


def decode_winrm_json(response):
    """Accept only one bounded, unambiguous successful JSON reply.

    Never inspect or propagate remote stderr or transport exception strings.
    """
    # Properties of external transport replies are untrusted, including
    # WinRMError instances which might contain remote stderr or secrets.
    try:
        status = response.status_code
    except Exception:
        raise WinRMError('winrm_invalid_response') from None
    if type(status) is not int:
        raise WinRMError('winrm_invalid_response')
    if status != 0:
        raise WinRMError('winrm_remote_query_failed')
    try:
        output = response.std_out
    except Exception:
        raise WinRMError('winrm_invalid_response') from None
    if type(output) is not bytes or not 0 < len(output) <= 65536:
        raise WinRMError('winrm_invalid_response')
    try:
        return json.loads(output.decode('utf-8-sig'),
                          object_pairs_hook=_unique_keys,
                          parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError, OverflowError):
        raise WinRMError('winrm_invalid_response') from None
