
"""Windows RDS / RD Gateway and SSH jump profiles. No password handling.
Author: Abdelhalim Talbi.
"""
import ipaddress
import re

HOST=re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
COLLECTION=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,127}$")
USERNAME=re.compile(r"^[^\r\n\x00]{0,256}$")

def host(value):
    if not isinstance(value,str) or not value or value != value.strip():
        raise ValueError("Hôte de passerelle invalide")
    v=value[1:-1] if value.startswith("[") and value.endswith("]") else value
    try:return str(ipaddress.ip_address(v))
    except ValueError:pass
    if not HOST.fullmatch(v) or '..' in v or v.endswith('.') or v.startswith('-'):
        raise ValueError("Hôte de passerelle invalide")
    return v

def port(value,default):
    v=str(value or default)
    if not v.isdecimal() or not 1<=int(v)<=65535:
        raise ValueError("Port de passerelle invalide")
    return int(v)

def parse_jump_chain(value):
    """Additional hops after first bastion: user@hostname:port separated by commas.

    No passwords, shell syntax or ambiguous IPv6 forms; at most 3 extra hops.
    """
    if not isinstance(value,str) or len(value)>768:raise ValueError('Chaîne SSH trop longue')
    if not value:return []
    parts=value.split(',')
    if not 1<=len(parts)<=3:raise ValueError('Maximum trois rebonds supplémentaires')
    hops=[]
    for part in parts:
        if part!=part.strip() or not part or any(c in part for c in '\r\n\x00\t '):
            raise ValueError('Format de rebond SSH invalide')
        if part.count('@')>1:raise ValueError('Utilisateur SSH invalide')
        user,endpoint=part.split('@',1) if '@' in part else ('',part)
        if user and (not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',user) or user.startswith('-')):
            raise ValueError('Utilisateur SSH invalide')
        if endpoint.count(':')>1:raise ValueError('IPv6 : utiliser un nom DNS dans la chaîne SSH')
        name,number=endpoint.rsplit(':',1) if ':' in endpoint else (endpoint,'22')
        hops.append({'host':host(name),'port':port(number,22),'user':user})
    if len({(h['host'].lower(),h['port']) for h in hops})!=len(hops):
        raise ValueError('Rebond SSH dupliqué')
    return hops

def validate_route(route):
    r={k:str((route or {}).get(k,'')).strip() for k in
       ('mode','gateway_host','gateway_user','gateway_port','collection','jump_host','jump_user','jump_port','jump_chain','vault_ref')}
    if r['mode'] not in ('','direct','rd_gateway','rds_collection','ssh_jump'):
        raise ValueError("Mode de rebond inconnu")
    if r['mode'] in ('rd_gateway','rds_collection'):
        r['gateway_host']=host(r['gateway_host'])
        r['gateway_port']=str(port(r['gateway_port'],443))
        if r['collection'] and not COLLECTION.fullmatch(r['collection']):
            raise ValueError("Collection RDS invalide")
        if r['mode']=='rds_collection' and not r['collection']:
            raise ValueError("Collection RDS requise")
    if r['mode']=='ssh_jump':
        r['jump_host']=host(r['jump_host'])
        r['jump_port']=str(port(r['jump_port'],22))
    if r['jump_chain']:
        if r['mode']!='ssh_jump':raise ValueError('Chaîne SSH réservée au rebond SSH')
        parse_jump_chain(r['jump_chain'])
    for key in ('gateway_user','jump_user','vault_ref'):
        if not USERNAME.fullmatch(r[key]):
            raise ValueError("Champ de rebond invalide")
    return r

def ssh_jump_args(route):
    r=validate_route(route)
    if r['mode']!='ssh_jump':return []
    if any(c in r['jump_user'] for c in '@:/\\ ') or r['jump_user'].startswith('-'):
        raise ValueError("Utilisateur rebond SSH invalide")
    hops=[{'host':r['jump_host'],'port':int(r['jump_port']),'user':r['jump_user']}]+parse_jump_chain(r['jump_chain'])
    endpoints=[]
    for hop in hops:
        if hop['user'] and (hop['user'].startswith('-') or any(c in hop['user'] for c in '@:/\\ ')):
            raise ValueError('Utilisateur rebond SSH invalide')
        endpoint=(hop['user']+'@' if hop['user'] else '')+hop['host']
        if ':' in hop['host']:endpoint=(hop['user']+'@' if hop['user'] else '')+'['+hop['host']+']'
        endpoints.append(endpoint+(':'+str(hop['port']) if hop['port']!=22 else ''))
    return ['-J',','.join(endpoints)]

def rdp_content(target,target_port='',username='',route=None):
    r=validate_route(route)
    if r['mode'] not in ('','direct','rd_gateway','rds_collection'):
        raise ValueError("Rebond incompatible avec RDP")
    target=host(target)
    p=port(target_port,3389)
    if not USERNAME.fullmatch(username):raise ValueError("Utilisateur RDP invalide")
    lines=[f'full address:s:{target}:{p}', 'prompt for credentials:i:1',
           'authentication level:i:2','enablecredsspsupport:i:1']
    if username:lines.append('username:s:'+username)
    if r['mode'] in ('rd_gateway','rds_collection'):
        lines.extend(['gatewayhostname:s:'+r['gateway_host']+':'+r['gateway_port'],
                      'gatewayusagemethod:i:1','gatewayprofileusagemethod:i:1',
                      'promptcredentialonce:i:0'])
        if r['gateway_user']:lines.append('gatewayusername:s:'+r['gateway_user'])
        if r['collection']:
            lines.append('loadbalanceinfo:s:tsv://MS Terminal Services Plugin.1.'+r['collection'])
    return '\r\n'.join(lines)+'\r\n'
