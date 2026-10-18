"""Pure UI action availability rules; no network side effects. Author: Abdelhalim Talbi."""

def primary_action_state(connection):
    """Enable actions only when their prerequisites exist."""
    valid = isinstance(connection, dict) and isinstance(connection.get('id'), str) and bool(connection['id'].strip())
    protocol = str(connection.get('protocol', '')).upper() if valid else ''
    return {'connect': valid, 'check_access': valid, 'sftp': valid and protocol in ('SSH', 'SFTP')}
