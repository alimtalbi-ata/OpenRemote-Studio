"""Single fail-closed preflight for UI reconnect entry points.
Author: Abdelhalim Talbi.
"""
from session_reconnect_choices import reconnect_choice_still_valid


def resolve_reconnect_target(registry, connections, connection_id, pid):
    """Return (connection, reason) after checking current process and catalog state.

    No launch and no process mutation occurs here. Callers must retain the
    registry's own final reconnect_candidate check immediately before launch.
    """
    if not isinstance(connection_id, str) or not connection_id.strip():
        return None, 'invalid_connection'
    if not isinstance(connections, (list, tuple)):
        return None, 'invalid_catalog'
    matches = [item for item in connections if isinstance(item, dict)
               and item.get('id') == connection_id]
    if len(matches) != 1:
        return None, 'missing_or_ambiguous_connection'
    try:
        rows = registry.snapshot()
    except Exception:
        return None, 'snapshot_unavailable'
    if not reconnect_choice_still_valid(rows, connection_id, pid):
        return None, 'session_unavailable'
    return matches[0], None
