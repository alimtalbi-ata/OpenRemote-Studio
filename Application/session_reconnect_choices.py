"""Safe reconnect choices for a connection, independent of Qt. Author: Abdelhalim Talbi."""
from session_selection import session_identity, selected_session
from session_presentation import selected_reconnect_allowed

def reconnectable_processes(rows, connection_id):
    """Return uniquely identified exited processes only if no sibling is active."""
    if not isinstance(rows,(list,tuple)) or not isinstance(connection_id,str) or not connection_id:
        return []
    if any(isinstance(r,dict) and r.get('connection_id')==connection_id and r.get('status') in ('running','unknown') for r in rows):
        return []
    choices=[]
    seen=set()
    duplicated=set()
    for row in rows:
        identity=session_identity(row)
        if identity is not None and identity[0]==connection_id:
            if identity in seen: duplicated.add(identity)
            seen.add(identity)
    seen.clear()
    for row in rows:
        identity=session_identity(row)
        if identity is None or identity[0]!=connection_id or identity in seen or identity in duplicated:
            continue
        seen.add(identity)
        if selected_reconnect_allowed(rows,*identity):
            choices.append(selected_session(rows,*identity))
    return choices


def reconnect_choice_still_valid(rows, connection_id, pid):
    """Recheck the exact chosen process against a fresh snapshot before launch."""
    if not isinstance(rows, (list, tuple)):
        return False
    identity = session_identity({'connection_id': connection_id, 'pid': pid})
    if identity is None:
        return False
    return any(session_identity(row) == identity for row in reconnectable_processes(rows, connection_id))
