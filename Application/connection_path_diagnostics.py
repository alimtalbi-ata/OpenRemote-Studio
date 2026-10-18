"""Privacy-preserving, offline access dependency topology. Author: Abdelhalim Talbi."""
from connection_policy import connection_route
from gateways import parse_jump_chain

CHECKS = {
    'poste': 'Vérifier les prérequis du poste et du client local.',
    'pam': 'Vérifier le droit d’accès PAM, le bail et la disponibilité du coffre.',
    'bastion': 'Vérifier la connectivité et les autorisations du bastion SSH.',
    'rd_gateway': 'Vérifier RD Gateway, TLS et les politiques CAP/RAP.',
    'rds_collection': 'Vérifier le broker et les droits sur la collection RDS.',
    'cible': 'Vérifier le service distant, son port et les règles réseau.',
}

def topology(protocol, route=None):
    """Return a redacted dependency chain, never a network probe or credential lookup."""
    if protocol not in ('SSH','SFTP','RDP','VNC','WEB'):
        raise ValueError('protocole inconnu')
    r=connection_route(protocol,route)
    mode=r['mode'] or 'direct'
    nodes=[{'kind':'poste','label':'Poste / client local'}]
    if r['vault_ref']:
        nodes.append({'kind':'pam','label':'Coffre PAM (référence seulement)'})
    if mode=='ssh_jump':
        nodes.append({'kind':'bastion','label':'Bastion SSH 1'})
        for index,_ in enumerate(parse_jump_chain(r['jump_chain']),start=2):
            nodes.append({'kind':'bastion','label':f'Bastion SSH {index}'})
    elif mode in ('rd_gateway','rds_collection'):
        nodes.append({'kind':'rd_gateway','label':'Passerelle RD Gateway'})
        if mode=='rds_collection':
            nodes.append({'kind':'rds_collection','label':'Collection RDS'})
    nodes.append({'kind':'cible','label':f'Cible {protocol}'})
    return {'schema':'openremote.path.v1','protocol':protocol,'mode':mode,
            'network_tested':False,'credentials_accessed':False,
            'nodes':[dict(node,status='non_verifie',check=CHECKS[node['kind']]) for node in nodes]}

def format_topology(result):
    if result.get('schema')!='openremote.path.v1' or result.get('network_tested') is not False or result.get('credentials_accessed') is not False:
        raise ValueError('rapport invalide')
    nodes=result.get('nodes')
    if not isinstance(nodes,list) or not nodes or any(n.get('kind') not in CHECKS or n.get('status')!='non_verifie' or not isinstance(n.get('label'),str) for n in nodes):
        raise ValueError('étapes invalides')
    # Labels are generated internally, not accepted from untrusted report data.
    return ('Parcours de connexion (hors ligne)\nAucune étape testée ni authentifiée.\n\n'
            + ' → '.join(n['label'] for n in nodes)
            + '\n\n' + '\n'.join(f"{i}. {n['label']} — non vérifié\n   {CHECKS[n['kind']]}" for i,n in enumerate(nodes,1)))
