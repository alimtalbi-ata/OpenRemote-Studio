"""Opt-in TCP reachability check, never authenticates. Author: Abdelhalim Talbi."""
import socket
from urllib.parse import urlsplit
from network_error_reporting import safe_tcp_error_message

def endpoint(connection):
    protocol=str(connection.get('protocol','')).upper()
    host=str(connection.get('host','')).strip()
    if protocol=='WEB':
        parts=urlsplit(host if '://' in host else 'https://'+host)
        if not parts.hostname: raise ValueError('Hôte WEB manquant')
        if parts.username or parts.password: raise ValueError('URL avec identifiants refusée')
        return parts.hostname,parts.port or (80 if parts.scheme=='http' else 443)
    defaults={'SSH':22,'SFTP':22,'RDP':3389,'VNC':5900}
    if protocol not in defaults: raise ValueError('Protocole non pris en charge')
    if not host or any(ch in host for ch in '/\\@?#'):
        raise ValueError('Hôte invalide')
    port=connection.get('port') or defaults[protocol]
    try: port=int(port)
    except (TypeError,ValueError): raise ValueError('Port invalide') from None
    if not 1<=port<=65535: raise ValueError('Port hors plage')
    return host,port

def probe(connection,timeout=2.0,connector=None):
    host,port=endpoint(connection)
    if not 0<float(timeout)<=10: raise ValueError('Délai invalide')
    dial=connector or socket.create_connection
    try:
        sock=dial((host,port),timeout=float(timeout))
        sock.close()
        return {'reachable':True,'host':host,'port':port,'message':'Port TCP accessible ; authentification non vérifiée.'}
    except (OSError,TimeoutError) as exc:
        return {'reachable':False,'host':host,'port':port,
                'message':f'Connexion TCP impossible : {safe_tcp_error_message(exc)}'}


def route_probe_notice(route):
    """State the scope of a local TCP check without implying hop traversal."""
    if not isinstance(route,dict):
        raise ValueError('Route invalide')
    mode=str(route.get('mode') or 'direct')
    if mode=='direct':
        return 'Test direct depuis ce poste vers la cible ; aucun contrôle d’authentification.'
    descriptions={'ssh_jump':'rebond SSH','rd_gateway':'passerelle RD Gateway',
                  'rds':'infrastructure RDS'}
    kind=descriptions.get(mode,'route configurée')
    return ('Attention : '+kind+' configuré(e). Le test TCP vérifie uniquement la cible '
            'depuis ce poste ; il ne traverse pas la route et ne valide pas la passerelle.')


def route_hops(connection,route):
    """Describe independent TCP checkpoints; never claim to traverse a gateway."""
    from gateways import validate_route
    checked=validate_route(route)
    target_host,target_port=endpoint(connection)
    mode=checked['mode'] or 'direct'
    hops=[]
    if mode=='ssh_jump':
        hops.append({'role':'bastion SSH','host':checked['jump_host'],'port':int(checked['jump_port']),
                     'scope':'direct depuis ce poste'})
    elif mode in ('rd_gateway','rds_collection'):
        hops.append({'role':'passerelle RD Gateway','host':checked['gateway_host'],
                     'port':int(checked['gateway_port']),'scope':'direct depuis ce poste'})
    hops.append({'role':'cible','host':target_host,'port':target_port,
                 'scope':'direct depuis ce poste (sans traverser la passerelle)' if hops else 'direct depuis ce poste'})
    return hops
