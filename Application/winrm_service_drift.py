"""R98: bounded, local-only WinRM service state drift; never queries the network.

Only compare rows present in BOTH snapshots. A truncated first-128 response is
not a complete inventory, so additions/removals are intentionally not inferred.
Author: Abdelhalim Talbi.
"""

MAX_SERVICES = 128
_STATES = frozenset(('Running', 'Stopped', 'Paused', 'Start Pending',
                     'Stop Pending', 'Continue Pending', 'Pause Pending', 'Unknown'))
_MODES = frozenset(('Auto', 'Manual', 'Disabled', 'Boot', 'System'))


class ServiceDriftError(ValueError):
    def __init__(self):
        super().__init__('winrm_invalid_response')


def _index(rows):
    if not isinstance(rows, list) or len(rows) > MAX_SERVICES:
        raise ServiceDriftError()
    found = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'name', 'display_name', 'state', 'start_mode'}:
            raise ServiceDriftError()
        name, label, state, mode = (row[k] for k in ('name', 'display_name', 'state', 'start_mode'))
        if (not isinstance(name, str) or not name or len(name) > 256
                or not isinstance(label, str) or len(label) > 256
                or any(ord(c) < 32 or ord(c) == 127 for c in name + label)
                or not isinstance(state, str) or not isinstance(mode, str)
                or state not in _STATES or mode not in _MODES):
            raise ServiceDriftError()
        key = name.casefold()
        if key in found:
            raise ServiceDriftError()
        found[key] = row
    return found


def compare_service_snapshots(previous, current, *, previous_truncated, current_truncated):
    """Compare two sanitized snapshots, with no guessed removals on truncation.

    Returns bounded state/mode transitions and complete-inventory membership
    changes. Never returns credentials, arbitrary response fields, or exceptions.
    """
    if type(previous_truncated) is not bool or type(current_truncated) is not bool:
        raise ServiceDriftError()
    old, new = _index(previous), _index(current)
    transitions = []
    for key in sorted(old.keys() & new.keys()):
        before, after = old[key], new[key]
        if before['state'] != after['state'] or before['start_mode'] != after['start_mode']:
            transitions.append({'name': after['name'], 'before_state': before['state'],
                                'after_state': after['state'],
                                'before_mode': before['start_mode'],
                                'after_mode': after['start_mode']})
    complete = not previous_truncated and not current_truncated
    added = sorted((new[k]['name'] for k in new.keys() - old.keys()), key=str.casefold) if complete else []
    removed = sorted((old[k]['name'] for k in old.keys() - new.keys()), key=str.casefold) if complete else []
    return {'transitions': transitions, 'added': added, 'removed': removed,
            'membership_complete': complete}
