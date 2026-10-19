"""Pure, non-network session overview presentation. Author: Abdelhalim Talbi."""

import unicodedata
from session_selection import selected_session

def session_status_label(row):
    if not isinstance(row, dict): return 'État local inconnu'
    status=row.get('status')
    if status=='running':return 'Active (processus local)'
    if status=='exited':
        code=row.get('exit_code')
        if code is None:return 'Terminée (code inconnu)'
        if code==0:return 'Terminée (code 0)'
        return f'Erreur locale (code {code})'
    return 'État local inconnu'

def session_empty_message(total, query='', state='all'):
    if not total:return 'Aucun processus suivi. Ouvrez une connexion pour commencer.'
    if str(query).strip() or state!='all':return 'Aucune session ne correspond aux filtres. Effacez la recherche ou choisissez Toutes.'
    return ''

def can_reconnect(row):
    return isinstance(row, dict) and row.get('status') == 'exited'


def selected_reconnect_allowed(rows, connection_id, pid):
    """Permit reconnect only for the exact selected exited process, with no active sibling."""
    if connection_id is None or pid is None:return False
    selected=selected_session(rows, connection_id, pid)
    if not can_reconnect(selected):return False
    return not any(r.get('connection_id')==connection_id and r.get('status') in ('running','unknown') for r in rows)


def session_visual_state(row):
    """Semantic state for a local process; never imply remote connectivity."""
    if not isinstance(row, dict):
        return ('unknown', 'État du processus local inconnu')
    status=row.get('status')
    if status=='running':
        return ('running', 'Processus local actif ; connexion distante non vérifiée')
    if status=='exited':
        code=row.get('exit_code')
        if code==0:return ('completed', 'Processus terminé avec code 0 ; résultat distant non vérifié')
        if code is None:return ('unknown', 'Processus terminé ; code de sortie indisponible')
        return ('failed', f'Processus terminé avec erreur locale (code {code})')
    return ('unknown', 'État du processus local inconnu')


def session_process_details(row):
    """Present only local process metadata; do not expose command lines or credentials."""
    if not isinstance(row, dict):
        raise ValueError('Session invalide')
    fields = (('Connexion', 'name'), ('Protocole', 'protocol'), ('PID', 'pid'),
              ('État local', 'status'), ('Démarrage UTC', 'started_at'),
              ('Code de sortie', 'exit_code'))
    def safe(value):
        if value is None: return 'indisponible'
        return ''.join(' ' if unicodedata.category(c).startswith('C') else c for c in str(value))[:200]
    return '\n'.join(f'{label} : {safe(row.get(key))}' for label, key in fields) + \
        '\nLe processus local ne garantit pas l’état distant.'


def session_visibility_summary(total, visible):
    """Describe the filtered local-process list without implying remote health."""
    if total < 0 or visible < 0 or visible > total:
        raise ValueError('Compteurs de sessions invalides')
    return f'{visible} processus affiché(s) sur {total} suivi(s) localement'
