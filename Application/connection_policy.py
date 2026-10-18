
"""Single policy for connection routes; no implicit credential injection.
Author: Abdelhalim Talbi.
"""
from gateways import validate_route
def connection_route(protocol, route, integrated=False):
    r=validate_route(route)
    mode=r['mode'] or 'direct'
    if mode in ('rd_gateway','rds_collection') and protocol!='RDP':
        raise ValueError('RD Gateway/RDS utilisable uniquement avec RDP')
    if mode=='ssh_jump' and protocol not in ('SSH','SFTP'):
        raise ValueError('ProxyJump utilisable uniquement avec SSH/SFTP')
    if integrated and protocol=='SFTP' and mode=='ssh_jump':
        raise ValueError('Le navigateur SFTP intégré ne gère pas ProxyJump')
    return r
