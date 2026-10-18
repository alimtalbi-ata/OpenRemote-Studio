"""Local-only trend comparison for shared dependencies. Author: Abdelhalim Talbi."""
from datetime import datetime, timezone, timedelta
from dependency_temporal import compare_temporal


def compare_dependency_trends(connections, routes, dashboard, sessions, probes, *, now=None, minutes=30, tolerance_seconds=60):
    """Compare equal adjacent time windows without implying remote root cause."""
    if type(minutes) is not int or not 1 <= minutes <= 720:
        raise ValueError('invalid minutes')
    if type(tolerance_seconds) is not int or not 0 <= tolerance_seconds <= 3600:
        raise ValueError('invalid tolerance')
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError('timezone-aware now required')
    now = now.astimezone(timezone.utc)
    previous = compare_temporal(connections, routes, dashboard, sessions, probes, now=now-timedelta(minutes=minutes), minutes=minutes, tolerance_seconds=tolerance_seconds)
    current = compare_temporal(connections, routes, dashboard, sessions, probes, now=now, minutes=minutes, tolerance_seconds=tolerance_seconds)
    def identity(group):
        return group['dependency_type'], tuple(group['connection_ids'])
    before = {identity(g):g for g in previous['groups']}
    rows=[]
    for group in current['groups']:
        old=before.get(identity(group),{})
        past=old.get('observed_error_events',0)
        present=group['observed_error_events']
        delta=present-past
        rows.append({'dependency_type':group['dependency_type'],
                     'connection_ids':list(group['connection_ids']),
                     'connections':group['connections'],
                     'previous_errors':past,'current_errors':present,
                     'delta':delta,'trend':'hausse' if delta>0 else ('baisse' if delta<0 else 'stable'),
                     'simultaneous_windows':group['overlap_windows'],
                     'max_simultaneous_connections':group['max_simultaneous_connections'],
                     'recommendation':('Examiner les chronologies des connexions du groupe.' if present else
                                       'Aucun échec local observé dans la période actuelle.'),
                     'remote_cause_confirmed':False})
    rows.sort(key=lambda g:(-g['delta'],-g['current_errors'],g['dependency_type'],g['connection_ids']))
    return {'schema':'openremote.dependency_trends.v1','scope':'local_only',
            'minutes_per_period':minutes,'remote_cause_confirmed':False,'groups':rows,
            'note':'Comparaison des événements locaux uniquement, sans attribution de cause distante.'}
