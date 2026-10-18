"""Human-readable local access path. No network or secret access.
Author: Abdelhalim Talbi.
"""
from connection_policy import connection_route
from gateways import parse_jump_chain

def describe_path(connection,route=None):
    r=connection_route(connection['protocol'],route)
    mode=r['mode'] or 'direct'
    target=connection['host']
    protocol=connection['protocol']
    if mode=='rd_gateway':
        path=f"Poste Windows → RD Gateway {r['gateway_host']}:{r['gateway_port']} → {target}"
    elif mode=='rds_collection':
        path=f"Poste Windows → RD Gateway {r['gateway_host']}:{r['gateway_port']} → collection RDS {r['collection']} → {target}"
    elif mode=='ssh_jump':
        extra=parse_jump_chain(r.get('jump_chain',''))
        path=f"Poste → bastion SSH {r['jump_host']}:{r['jump_port']}"
        for hop in extra:path+=f" → bastion SSH {hop['host']}:{hop['port']}"
        path+=f' → {target}'
    else:path=f"Poste → {target}"
    result=['Parcours : '+path,'Protocole : '+protocol]
    if r.get('vault_ref'):
        result.append('PAM : référence documentaire uniquement (aucun secret récupéré)')
    if mode in ('rd_gateway','rds_collection'):
        result.append('Authentification : invite Windows mstsc ; aucun mot de passe dans le fichier RDP')
    return result
