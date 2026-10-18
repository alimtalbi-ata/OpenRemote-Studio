"""Read-only filtering and evidence-based priority of shared-route incidents.
No remote root-cause attribution. Author: Abdelhalim Talbi.
"""

def incident_priority(group):
    """Priority of LOCAL observations, not the severity of a remote incident."""
    if not isinstance(group, dict):
        raise ValueError('invalid group')
    overlap=group.get('overlap_windows',0)
    simultaneous=group.get('max_simultaneous_connections',0)
    affected=group.get('affected_connections',0)
    if any(type(n) is not int or n<0 for n in (overlap,simultaneous,affected)):
        raise ValueError('invalid counters')
    if overlap>0 and simultaneous>=3:
        return 'forte'
    if overlap>0 and simultaneous>=2:
        return 'moderee'
    if affected>0:
        return 'a_examiner'
    return 'sans_echec'

def visible_group_indices(groups, mode='ALL'):
    if not isinstance(groups,list) or mode not in ('ALL','AFFECTED','SIMULTANEOUS'):
        raise ValueError('invalid filter')
    result=[]
    for index,group in enumerate(groups):
        if not isinstance(group,dict):
            continue
        priority=incident_priority(group)
        if mode=='AFFECTED' and priority=='sans_echec':
            continue
        if mode=='SIMULTANEOUS' and group.get('overlap_windows',0)==0:
            continue
        result.append(index)
    return result
