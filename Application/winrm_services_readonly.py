"""R95: bounded read-only Windows service inventory over opt-in HTTPS WinRM.

Never executes user-provided PowerShell. Never logs credentials or raw stderr.
Author: Abdelhalim Talbi.
"""
import json
from winrm_readonly import WinRMReadOnly, WinRMError, _text

# Fixed query, no operator input or interpolated credentials.
_SERVICES_PS = r'''
$ErrorActionPreference = 'Stop'
@(Get-CimInstance -ClassName Win32_Service |
  Sort-Object Name | Select-Object -First 128 Name, DisplayName, State, StartMode) |
  ConvertTo-Json -Compress -Depth 3
'''.strip()
_STATES = frozenset(('Running', 'Stopped', 'Paused', 'Start Pending',
                     'Stop Pending', 'Continue Pending', 'Pause Pending', 'Unknown'))
_MODES = frozenset(('Auto', 'Manual', 'Disabled', 'Boot', 'System'))


def _normalize_services(raw):
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or len(raw) > 128:
        raise WinRMError('winrm_invalid_response')
    seen = set()
    services = []
    for row in raw:
        if not isinstance(row, dict):
            raise WinRMError('winrm_invalid_response')
        name = _text(row.get('Name'), 256)
        label = _text(row.get('DisplayName'), 256)
        state = _text(row.get('State'), 32)
        mode = _text(row.get('StartMode'), 32)
        if not name or name.casefold() in seen or state not in _STATES or mode not in _MODES:
            raise WinRMError('winrm_invalid_response')
        seen.add(name.casefold())
        services.append({'name': name, 'display_name': label,
                         'state': state, 'start_mode': mode})
    return {'state': 'ok', 'read_only': True, 'services': services,
            'limit': 128, 'may_be_truncated': len(services) == 128}


class WinRMServicesReadOnly(WinRMReadOnly):
    """Optional GET-equivalent inventory; never starts/stops services."""

    def services(self, *, online=False, cancelled=None):
        if not online:
            return {'state': 'offline', 'read_only': True, 'services': []}
        if cancelled is not None and not callable(cancelled):
            raise WinRMError('winrm_invalid_cancellation')
        if cancelled is not None and cancelled():
            raise WinRMError('winrm_cancelled')
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
        try:
            session = self._factory(self._endpoint, self._username, password,
                                    timeout=self._timeout)
            response = session.run_ps(_SERVICES_PS)
        except WinRMError:
            raise
        except Exception:
            raise WinRMError('winrm_transport_unavailable') from None
        finally:
            password = None
        if cancelled is not None and cancelled():
            raise WinRMError('winrm_cancelled')
        if getattr(response, 'status_code', None) != 0:
            raise WinRMError('winrm_remote_query_failed')
        output = getattr(response, 'std_out', None)
        if not isinstance(output, bytes) or len(output) > 65536:
            raise WinRMError('winrm_invalid_response')
        try:
            parsed = json.loads(output.decode('utf-8-sig'))
        except (UnicodeDecodeError, ValueError):
            raise WinRMError('winrm_invalid_response') from None
        return _normalize_services(parsed)
