"""Dashboard metrics and command palette, free of Qt dependencies."""
from tool_catalog import TOOLS

def summarize(connections, workspace):
    ids={c['id'] for c in connections}
    recent=[i for i in workspace.get('recent',[]) if i in ids][:8]
    favorites=[i for i in workspace.get('favorites',[]) if i in ids]
    protocols={}
    for c in connections:
        p=c['protocol'];protocols[p]=protocols.get(p,0)+1
    return {'total':len(connections),'favorites':len(favorites),'recent':recent,'protocols':protocols}

def command_search(query,connections,limit=25):
    q=query.strip().casefold()
    items=[]
    for category,name,action,description in TOOLS:
        if not q or q in f'{category} {name} {description}'.casefold():
            items.append({'kind':'tool','label':f'{name} · {category}','action':action,'detail':description})
    for c in connections:
        if not q or q in ' '.join(str(c.get(k,'')) for k in ('name','host','group','tags','protocol')).casefold():
            items.append({'kind':'connection','label':f"{c['name']} · {c['protocol']}",'action':c['id'],'detail':c['host']})
    return items[:limit]


def quick_access(connections,workspace,limit=12):
    """Stable favorite-first list without exposing secrets or stale IDs."""
    if not isinstance(limit,int) or not 1<=limit<=100:raise ValueError('Limite invalide')
    # Duplicate IDs are ambiguous: never offer an unsafe quick-launch target.
    counts={}
    for c in connections:
        identifier=c.get('id')
        if isinstance(identifier,str) and identifier.strip():
            counts[identifier]=counts.get(identifier,0)+1
    indexed={c['id']:c for c in connections if isinstance(c.get('id'),str) and counts.get(c['id'])==1}
    ids=[]
    for key in ('favorites','recent'):
        for identifier in workspace.get(key,[]):
            if identifier in indexed and identifier not in ids:ids.append(identifier)
    return [{'id':i,'name':indexed[i]['name'],'protocol':indexed[i]['protocol'],
             'host':indexed[i]['host'],'favorite':i in workspace.get('favorites',[])}
            for i in ids[:limit]]
