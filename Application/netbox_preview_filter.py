"""Pure, bounded NetBox comparison filtering. No I/O or secret-bearing fields.

Author: Abdelhalim Talbi.
"""

STATUSES = ('matched', 'missing_local', 'ambiguous', 'local_only')


class NetBoxFilterError(ValueError):
    """Stable, input-free failure code."""


def filter_preview(result, *, status='all', search=''):
    """Filter an existing comparison without another NetBox request.

    Only display-safe device/local-host projections are accessed. The full
    comparison counts remain available to the caller independently.
    """
    if status not in ('all',) + STATUSES or not isinstance(search, str) or len(search) > 120:
        raise NetBoxFilterError('netbox_filter_invalid_input')
    if any(ord(c) < 32 or ord(c) == 127 for c in search):
        raise NetBoxFilterError('netbox_filter_invalid_input')
    if not isinstance(result, dict) or result.get('state') != 'ok':
        raise NetBoxFilterError('netbox_filter_invalid_snapshot')
    rows = result.get('rows')
    if not isinstance(rows, list) or len(rows) > 15000:
        raise NetBoxFilterError('netbox_filter_invalid_snapshot')
    term = search.strip().casefold()
    visible = []
    for row in rows:
        if not isinstance(row, dict) or row.get('status') not in STATUSES:
            raise NetBoxFilterError('netbox_filter_invalid_row')
        device, host = row.get('device'), row.get('local_host')
        if (not isinstance(device, str) or len(device) > 160 or
                not isinstance(host, str) or len(host) > 253 or
                any(ord(c) < 32 or ord(c) == 127 for c in device + host)):
            raise NetBoxFilterError('netbox_filter_invalid_row')
        if (status == 'all' or row['status'] == status) and (not term or term in device.casefold() or term in host.casefold()):
            visible.append({'status': row['status'], 'device': device, 'local_host': host})
    return {'rows': visible, 'visible': len(visible), 'total': len(rows)}
