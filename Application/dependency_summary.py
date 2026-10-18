"""Read-only compact dependency trend summary. Author: Abdelhalim Talbi."""

def summarize_trends(report, *, limit=8, affected_only=False):
    if not isinstance(report,dict) or not isinstance(report.get('groups'),list):
        raise ValueError('invalid report')
    if type(limit) is not int or not 1 <= limit <= 100 or type(affected_only) is not bool:
        raise ValueError('invalid options')
    rows=[]
    for group in report['groups']:
        if not isinstance(group,dict):
            continue
        try:
            current=group['current_errors']; previous=group['previous_errors']
            simultaneous=group['simultaneous_windows']; count=group['connections']
            if any(type(x) is not int or x<0 for x in (current,previous,simultaneous,count)):
                continue
            if affected_only and current==0:
                continue
            rows.append({'dependency_type':str(group['dependency_type']),
                         'connections':count,'previous':previous,'current':current,
                         'delta':current-previous,'simultaneous':simultaneous,
                         'connection_ids':tuple(x for x in group.get('connection_ids',[]) if isinstance(x,str) and x)})
        except (KeyError,TypeError):
            continue
    rows.sort(key=lambda x:(-int(x['simultaneous']>0),-x['delta'],-x['current'],x['dependency_type']))
    return rows[:limit]


def resolve_group_connections(row, available_ids):
    """Return only current inventory identities from a displayed dependency row."""
    if not isinstance(row,dict) or not isinstance(available_ids,(set,frozenset)):
        raise ValueError('invalid selection')
    identities=row.get('connection_ids',())
    if not isinstance(identities,(list,tuple)):
        return []
    return sorted({identity for identity in identities if isinstance(identity,str) and identity in available_ids})
