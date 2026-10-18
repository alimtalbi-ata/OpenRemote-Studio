"""Stable session selection and snapshot helpers (no Qt/network access). Author: Abdelhalim Talbi."""

def session_identity(row):
    """Return a stable connection/PID identity, or None for malformed rows."""
    if not isinstance(row, dict):
        return None
    connection = row.get('connection_id')
    pid = row.get('pid')
    if not isinstance(connection, str) or not connection.strip() or connection != connection.strip() or pid is None or isinstance(pid, bool):
        return None
    pid_text = str(pid).strip()
    if not pid_text.isascii() or not pid_text.isdecimal() or int(pid_text) <= 0:
        return None
    return (connection, str(int(pid_text)))


def selected_session(rows, connection_id, pid):
    """Resolve an exact session without confusing sibling processes."""
    if not isinstance(rows, (list, tuple)) or not isinstance(connection_id, str):
        return None
    requested = session_identity({'connection_id': connection_id, 'pid': pid})
    if requested is None:
        return None
    matches = [row for row in rows if session_identity(row) == requested]
    # A duplicate process identity is ambiguous: fail closed rather than act on an arbitrary row.
    return matches[0] if len(matches) == 1 else None


def preserved_session_identity(rows, previous):
    """Keep selection only when the exact process still exists in the filtered rows."""
    if not isinstance(previous, tuple) or len(previous) != 2:
        return None
    requested = session_identity({"connection_id": previous[0], "pid": previous[1]})
    return requested if requested and selected_session(rows, *requested) is not None else None
