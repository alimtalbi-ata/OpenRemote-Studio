"""Safe selection of connections from a temporal dependency group. Author: Abdelhalim Talbi."""

def eligible_connection_ids(group, known_ids):
    """Return current inventory IDs only, preserving group order and removing duplicates."""
    if not isinstance(group,dict) or not isinstance(known_ids,(set,frozenset)):
        raise ValueError('invalid selection data')
    ids=group.get('connection_ids')
    if not isinstance(ids,list):
        raise ValueError('invalid group members')
    result=[]
    for identity in ids:
        if isinstance(identity,str) and identity in known_ids and identity not in result:
            result.append(identity)
    return result


def group_at_index(groups, index):
    """Resolve a sorted table row's original group index, fail closed."""
    if not isinstance(groups,list) or isinstance(index,bool) or not isinstance(index,int):
        return None
    if index<0 or index>=len(groups):return None
    group=groups[index]
    return group if isinstance(group,dict) else None
