"""Fail-closed, non-destructive NetBox/local connection comparison.

Author: Abdelhalim Talbi. No I/O, imports, writes, or secrets in output.
"""
from collections import defaultdict
from ipaddress import ip_address, ip_interface


class NetBoxPreviewError(ValueError):
    """Stable public error code; never contains an input value."""


def _host(value, *, cidr=False):
    if not isinstance(value, str) or not value or len(value) > 253:
        return ''
    value = value.strip().lower().rstrip('.')
    if cidr:
        try:
            return str(ip_interface(value).ip)
        except ValueError:
            return ''
    if value.startswith('[') and value.endswith(']'):
        value = value[1:-1]
    try:
        return str(ip_address(value))
    except ValueError:
        pass
    if not value or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789.-' for c in value):
        return ''
    if value.startswith(('-', '.')) or '..' in value:
        return ''
    return value


def compare_inventory(snapshot, connections):
    """Compare trusted read-only projections; never change source objects.

    An ambiguous name/IP mapping is explicitly flagged, never silently matched.
    WEB URLs and all credentials, users, groups and tags are excluded.
    """
    if not isinstance(snapshot, dict) or snapshot.get('state') not in ('offline', 'ok'):
        raise NetBoxPreviewError('netbox_preview_invalid_snapshot')
    if snapshot['state'] == 'offline':
        return {'state': 'offline', 'read_only': True, 'rows': [], 'counts': {}}
    devices = snapshot.get('devices')
    if not isinstance(devices, list) or len(devices) > 5000 or not isinstance(connections, (list, tuple)) or len(connections) > 10000:
        raise NetBoxPreviewError('netbox_preview_invalid_snapshot')
    normalized_devices = []
    seen_ids = set()
    for item in devices:
        if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] <= 0 or item['id'] in seen_ids:
            raise NetBoxPreviewError('netbox_preview_invalid_device')
        seen_ids.add(item['id'])
        name = item.get('name')
        if not isinstance(name, str) or not name or len(name) > 160 or any(ord(c) < 32 for c in name):
            raise NetBoxPreviewError('netbox_preview_invalid_device')
        keys = set(filter(None, (_host(name), _host(item.get('primary_ip4', ''), cidr=True))))
        normalized_devices.append((item['id'], name, keys))
    local = []
    for item in connections:
        if not isinstance(item, dict):
            raise NetBoxPreviewError('netbox_preview_invalid_connection')
        if item.get('protocol') not in ('SSH', 'SFTP', 'RDP', 'VNC'):
            continue
        host = _host(item.get('host'))
        if host:
            local.append((host, item['protocol']))
    # Match by either device name or primary IPv4, without assuming unique names.
    by_key = defaultdict(set)
    for idx, (_, _, keys) in enumerate(normalized_devices):
        for key in keys:
            by_key[key].add(idx)
    local_keys = defaultdict(list)
    for idx, (host, _) in enumerate(local):
        local_keys[host].append(idx)
    matches = defaultdict(set)
    for key, indices in local_keys.items():
        for idx in indices:
            matches[idx].update(by_key.get(key, ()))
    rows = []
    involved_local = set()
    for idx, (identifier, name, keys) in enumerate(normalized_devices):
        candidates = {li for key in keys for li in local_keys.get(key, ())}
        involved_local.update(candidates)
        ambiguous = (len(candidates) > 1 or any(len(matches[li]) != 1 or
                     len(local_keys[local[li][0]]) > 1 for li in candidates))
        status = 'ambiguous' if candidates and ambiguous else 'matched' if candidates else 'missing_local'
        local_host = local[next(iter(candidates))][0] if status == 'matched' else ''
        rows.append({'status': status, 'device_id': identifier, 'device': name,
                     'local_host': local_host})
    for idx, (host, _) in enumerate(local):
        if idx not in involved_local:
            rows.append({'status': 'local_only', 'device_id': None, 'device': '',
                         'local_host': host})
    counts = {status: sum(row['status'] == status for row in rows)
              for status in ('matched', 'missing_local', 'ambiguous', 'local_only')}
    return {'state': 'ok', 'read_only': True, 'rows': rows, 'counts': counts}
