"""Read-only local operations dashboard; no network I/O. Author: Abdelhalim Talbi."""
from collections import Counter
from connection_timeline import timeline
from incident_correlation import correlate

def build_dashboard(connections, sessions, probes, now=None):
    if not isinstance(connections,(list,tuple)) or not isinstance(sessions,(list,tuple)) or not isinstance(probes,(list,tuple)):
        raise ValueError('invalid input')
    if len(connections)>10000 or len(sessions)>50000 or len(probes)>50000:
        raise ValueError('input too large')
    protocol_counts=Counter()
    rows=[]
    for c in connections:
        if not isinstance(c,dict) or not isinstance(c.get('id'),str) or not c['id']:
            continue
        proto=str(c.get('protocol','UNKNOWN')).upper()
        if proto not in ('SSH','RDP','VNC','SFTP','WEB','TELNET','LOCAL'):
            proto='OTHER'
        protocol_counts[proto]+=1
        events=timeline(sessions,probes,c['id'],limit=500)
        incident=correlate(events,now=now)
        rows.append({'id':c['id'],'protocol':proto,'local_errors_30m':incident['count'],
                     'recurrent':incident['recurrent'],'observations':len(events),
                     'status':'attention' if incident['recurrent'] else ('observed' if events else 'not_tested')})
    rows.sort(key=lambda r:(-r['local_errors_30m'],-r['observations'],r['id']))
    return {'schema':'openremote.operations.v1','scope':'local_only','remote_health_verified':False,
            'connections':len(rows),'protocols':dict(sorted(protocol_counts.items())),
            'recurrent_local_failures':sum(r['recurrent'] for r in rows),
            'without_observations':sum(r['status']=='not_tested' for r in rows),
            'rows':rows}
