"""Unified SSH hop path model, without secrets or network side effects. Author: Abdelhalim Talbi."""
from jump_chain_editor import validate_hop, encode_chain, decode_chain
from gateways import validate_route

def route_to_hops(route):
    r=validate_route(route)
    if r['mode']!='ssh_jump':raise ValueError('Le parcours doit utiliser ssh_jump')
    hops=[validate_hop(r['jump_host'],r['jump_port'],r['jump_user'])]+decode_chain(r['jump_chain'])
    validate_path(hops)
    return hops

def validate_path(hops):
    if not isinstance(hops,(list,tuple)) or not 1<=len(hops)<=4:
        raise ValueError('Le parcours SSH doit contenir entre un et quatre bastions')
    checked=[validate_hop(h['host'],h.get('port',22),h.get('user','')) for h in hops]
    identities=[(h['host'].casefold(),h['port']) for h in checked]
    if len(identities)!=len(set(identities)):
        raise ValueError('Bastion dupliqué dans le parcours SSH')
    encode_chain(checked[1:])
    return checked

def hops_to_route(hops,base=None):
    checked=validate_path(hops)
    base=dict(base or {})
    base.update(mode='ssh_jump',jump_host=checked[0]['host'],jump_port=str(checked[0]['port']),
                jump_user=checked[0]['user'],jump_chain=encode_chain(checked[1:]))
    return validate_route(base)

def path_preview(hops,target=None):
    checked=validate_path(hops)
    nodes=[f"{i}. {h['user']+'@' if h['user'] else ''}{h['host']}:{h['port']}" for i,h in enumerate(checked,1)]
    if target:nodes.append('Cible : '+str(target))
    return ' → '.join(nodes)
