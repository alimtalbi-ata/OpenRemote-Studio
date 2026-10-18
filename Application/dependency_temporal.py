"""Conservative temporal overlap of local failures for shared access routes.
No network I/O, remote attribution, hostnames, or credentials in output.
Author: Abdelhalim Talbi.
"""
from datetime import datetime, timezone, timedelta
from connection_timeline import timeline
from shared_dependency_analysis import compare_dependencies

def compare_temporal(connections, routes, dashboard, sessions, probes, *, now=None, minutes=30, tolerance_seconds=60):
    if type(minutes) is not int or not 1 <= minutes <= 1440:
        raise ValueError('invalid time window')
    if type(tolerance_seconds) is not int or not 0 <= tolerance_seconds <= 3600:
        raise ValueError('invalid tolerance')
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError('timezone-aware now required')
    now=now.astimezone(timezone.utc)
    cutoff=now-timedelta(minutes=minutes)
    base=compare_dependencies(connections,routes,dashboard)
    ids={identity for group in base['groups'] for identity in group['connection_ids']}
    times={}
    for identity in ids:
        events=timeline(sessions,probes,identity,limit=500,kind='error')
        parsed=[]
        for event in events:
            try:
                stamp=datetime.fromisoformat(event['at'].replace('Z','+00:00')).astimezone(timezone.utc)
            except (ValueError,TypeError,KeyError,AttributeError):
                continue
            if cutoff <= stamp <= now:
                parsed.append(stamp)
        times[identity]=sorted(parsed)
    groups=[]
    for group in base['groups']:
        members=group['connection_ids']
        # Each cluster is anchored to its earliest event; avoid transitive chaining.
        observations=sorted((stamp,identity) for identity in members for stamp in times[identity])
        clusters=[]
        for stamp,identity in observations:
            if not clusters or (stamp-clusters[-1][0]).total_seconds()>tolerance_seconds:
                clusters.append((stamp,{identity}))
            else:
                clusters[-1][1].add(identity)
        overlapping=[(stamp,matched) for stamp,matched in clusters if len(matched)>=2]
        groups.append({**group,
            'window_minutes':minutes,'tolerance_seconds':tolerance_seconds,
            'observed_error_events':len(observations),
            'overlap_windows':len(overlapping),
            'max_simultaneous_connections':max((len(m) for _,m in overlapping),default=0),
            'overlapping_connection_ids':sorted(set().union(*(m for _,m in overlapping))) if overlapping else [],
            'remote_cause_confirmed':False})
    groups.sort(key=lambda g:(-g['overlap_windows'],-g['max_simultaneous_connections'],-g['affected_connections'],g['dependency_type'],g['connection_ids']))
    return {'schema':'openremote.dependency_temporal.v1','scope':'local_only',
            'remote_cause_confirmed':False,'groups':groups,
            'skipped_invalid_routes':base['skipped_invalid_routes'],
            'note':'Co-occurrence of local failures does not prove a shared remote outage.'}
