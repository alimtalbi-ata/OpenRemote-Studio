"""R95: bounded read-only Windows service inventory over opt-in HTTPS WinRM.

Never executes user-provided PowerShell. Never logs credentials or raw stderr.
Author: Abdelhalim Talbi.
"""
from winrm_readonly import WinRMReadOnly, WinRMError, _text, _ca_bundle_digest, _snapshot_ca_bundle
from winrm_service_totals import unwrap_service_envelope, ServiceTotalError

# Fixed query, no operator input or interpolated credentials.
_SERVICES_PS = r'''
$ErrorActionPreference = 'Stop'
$all = @(Get-CimInstance -ClassName Win32_Service | Sort-Object Name)
@{ TotalCount = $all.Count; Services = @(
    $all | Select-Object -First 128 Name, DisplayName, State, StartMode
  ) } | ConvertTo-Json -Compress -Depth 4
'''.strip()
_STATES = frozenset(('Running', 'Stopped', 'Paused', 'Start Pending',
                     'Stop Pending', 'Continue Pending', 'Pause Pending', 'Unknown'))
_MODES = frozenset(('Auto', 'Manual', 'Disabled', 'Boot', 'System'))


def _normalize_services(raw):
    try:
        total_count, raw = unwrap_service_envelope(raw)
    except ServiceTotalError:
        raise WinRMError('winrm_invalid_response') from None
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
            'limit': 128, 'total_count': total_count,
            'may_be_truncated': (total_count > 128 if total_count is not None
                                 else len(services) == 128)}


class WinRMServicesReadOnly(WinRMReadOnly):
    """Optional GET-equivalent inventory; never starts/stops services."""

    def services(self, *, online=False, cancelled=None):
        if not online:
            return {'state': 'offline', 'read_only': True, 'services': []}
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
            # Make and verify the trust snapshot before reading WinCred; ACL
            # provisioning failure must not cause a credential lookup.
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
                    response = session.run_ps(_SERVICES_PS)
                # Never propagate raw provider or transport exception text.
                except Exception:
                    raise WinRMError('winrm_transport_unavailable') from None
        finally:
            password = None
        if cancelled is not None and cancelled():
            raise WinRMError('winrm_cancelled')
        from winrm_response import decode_winrm_json
        return _normalize_services(decode_winrm_json(response))