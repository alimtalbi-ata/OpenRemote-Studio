"""Validated, side-effect-free multi-hop editor model. Author: Abdelhalim Talbi."""
from gateways import host, port, parse_jump_chain
import re

MAX_EXTRA_HOPS=3

def validate_hop(name, number='22', user=''):
    if not isinstance(user,str) or (user and (not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',user) or user.startswith('-'))):
        raise ValueError('Utilisateur SSH invalide')
    name=host(name)
    if ':' in name:
        raise ValueError('IPv6 non pris en charge dans la chaîne de rebonds')
    return {'host':name,'port':port(number,22),'user':user}

def encode_chain(hops):
    if len(hops)>MAX_EXTRA_HOPS:raise ValueError('Maximum trois rebonds supplémentaires')
    checked=[validate_hop(h['host'],h.get('port',22),h.get('user','')) for h in hops]
    identities=[(h['host'].casefold(),h['port']) for h in checked]
    if len(identities)!=len(set(identities)):raise ValueError('Rebond SSH dupliqué')
    encoded=','.join((h['user']+'@' if h['user'] else '')+h['host']+(':'+str(h['port']) if h['port']!=22 else '') for h in checked)
    if len(encoded)>768:raise ValueError('Chaîne SSH trop longue')
    if parse_jump_chain(encoded)!=checked:raise ValueError('Chaîne SSH incohérente')
    return encoded

def decode_chain(value):
    return parse_jump_chain(value)

def insert_hop(hops,hop,index=None):
    result=[dict(h) for h in hops]
    if index is None:index=len(result)
    if not 0<=index<=len(result):raise ValueError('Position de rebond invalide')
    result.insert(index,hop)
    encode_chain(result)
    return result

def move_hop(hops,index,delta):
    result=[dict(h) for h in hops]
    target=index+delta
    if not 0<=index<len(result) or not 0<=target<len(result):raise ValueError('Position de rebond invalide')
    result[index],result[target]=result[target],result[index]
    return result

def remove_hop(hops,index):
    result=[dict(h) for h in hops]
    if not 0<=index<len(result):raise ValueError('Position de rebond invalide')
    result.pop(index)
    return result
