"""Group local errors by evidence type and time bucket, without remote attribution.
Author: Abdelhalim Talbi.
"""
from collections import Counter
from datetime import datetime, timezone, timedelta
from connection_timeline import timeline

KINDS = ('tcp_local', 'ssh_jump', 'session_exit')

def group_local_errors(sessions, probes, connection_id, *, now=None, minutes=60, limit=500):
    if not isinstance(connection_id,str) or not connection_id:
        raise ValueError('invalid connection id')
    if type(minutes) is not int or not 1 <= minutes <= 1440:
        raise ValueError('invalid time window')
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('invalid limit')
    now = now or datetime.now(timezone.utc)
    if not isinstance(now,datetime) or now.tzinfo is None:
        raise ValueError('timezone-aware now required')
    now = now.astimezone(timezone.utc)
    cutoff = now-timedelta(minutes=minutes)
    events = timeline(sessions,probes,connection_id,limit=limit,kind='error')
    counts=Counter()
    for event in events:
        try:
            at=datetime.fromisoformat(event['at'].replace('Z','+00:00')).astimezone(timezone.utc)
        except (ValueError,TypeError,KeyError,AttributeError):
            continue
        if not cutoff <= at <= now:
            continue
        if event.get('kind')=='session':
            category='session_exit'
        elif event.get('kind')=='probe' and event.get('detail') in ('tcp_local','ssh_jump'):
            category=event['detail']
        else:
            continue
        bucket=at.replace(minute=0,second=0,microsecond=0).isoformat()
        counts[(category,bucket)]+=1
    groups=[{'category':category,'hour_utc':hour,'count':count}
            for (category,hour),count in sorted(counts.items(),key=lambda p:(-p[1],p[0]))]
    return {'schema':'openremote.local_incidents.v1','scope':'local_only',
            'remote_cause_confirmed':False,'window_minutes':minutes,
            'total_errors':sum(counts.values()),'groups':groups}

def format_summary(report):
    if not isinstance(report,dict) or report.get('schema')!='openremote.local_incidents.v1':
        raise ValueError('invalid incident report')
    lines=['Échecs locaux observés : '+str(report['total_errors']),
           'Cause distante : non vérifiée.']
    for item in report['groups']:
        if item['category'] not in KINDS:raise ValueError('invalid category')
        lines.append(f"{item['category']} | {item['hour_utc']} | {item['count']}")
    if not report['groups']:lines.append('Aucun échec local observé dans la fenêtre sélectionnée.')
    return '\n'.join(lines)
