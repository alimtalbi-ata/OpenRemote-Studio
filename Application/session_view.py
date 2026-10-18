"""Pure session filtering and summary for Qt cockpit. Author: Abdelhalim Talbi."""
def filter_sessions(rows, query='', state='all'):
    if state not in ('all','running','exited','failed','unknown'):
        raise ValueError('Filtre de session inconnu')
    term=str(query).strip().casefold()
    result=[]
    for row in rows:
        if state=='failed':
            if row['status']!='exited' or row.get('exit_code') in (None,0):continue
        elif state!='all' and row['status']!=state:continue
        searchable=' '.join(str(row.get(k,'')) for k in ('name','protocol','pid','connection_id')).casefold()
        if term and term not in searchable:continue
        result.append(row)
    return result

def session_counts(rows):
    return {'total':len(rows),'running':sum(x['status']=='running' for x in rows),
            'exited':sum(x['status']=='exited' for x in rows),
            'failed':sum(x['status']=='exited' and x.get('exit_code') not in (None,0) for x in rows),
            'unknown':sum(x['status']=='unknown' for x in rows)}


def prioritized_sessions(rows):
    """Stable operational ordering: running, unknown, failed, successful exit.

    Never mutate the registry snapshot; preserve relative order within each class.
    A local PID is not proof of remote connectivity.
    """
    def priority(row):
        status=row.get('status')
        if status=='running':return 0
        if status=='unknown':return 1
        if status=='exited' and row.get('exit_code') not in (None,0):return 2
        if status=='exited':return 3
        return 4
    return sorted(rows,key=priority)
