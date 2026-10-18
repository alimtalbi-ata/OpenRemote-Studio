"""Pure validation of contextual dashboard actions. Author: Abdelhalim Talbi."""
ACTIONS = ('open','details','timeline','preflight','tcp')

def allowed_action(action, connection_id, known_ids):
    """Fail closed when a stale or unknown dashboard row is selected."""
    if not isinstance(action,str) or action not in ACTIONS:
        return False
    if not isinstance(connection_id,str) or not connection_id:
        return False
    if not isinstance(known_ids,(list,tuple,set,frozenset)):
        return False
    return connection_id in known_ids
