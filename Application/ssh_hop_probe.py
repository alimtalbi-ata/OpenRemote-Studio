"""Consent-only, bounded LOCAL TCP checks for each SSH bastion. No route validation.
Author: Abdelhalim Talbi.
"""
import socket
from ssh_path_editor import validate_path

def plan(hops):
    return tuple({'index':i,'host':h['host'],'port':h['port'],'role':'principal' if i==1 else 'rebond'}
                 for i,h in enumerate(validate_path(hops),1))

def classify_probe(index,connected):
    if not isinstance(index,int) or isinstance(index,bool) or not 1<=index<=4:
        raise ValueError('Indice de saut invalide')
    if connected is True:
        return {'index':index,'status':'tcp_open_local','message':f'Saut {index} : port TCP joignable depuis ce poste (SSH et chemin distant NON vérifiés).'}
    if connected is False:
        return {'index':index,'status':'tcp_unavailable_local','message':f'Saut {index} : port TCP inaccessible depuis ce poste (aucune conclusion sur les rebonds).'}
    return {'index':index,'status':'tcp_unknown_local','message':f'Saut {index} : résultat TCP indéterminé.'}

def check(hops,timeout=2,connector=None):
    if not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not 0.2<=timeout<=5:
        raise ValueError('Délai TCP invalide')
    items=plan(hops)
    connect=connector or socket.create_connection
    results=[]
    for item in items:
        try:
            sock=connect((item['host'],item['port']),timeout=timeout)
        except OSError:
            connected=False
        else:
            connected=True
            try:sock.close()
            except OSError:pass
        results.append(classify_probe(item['index'],connected))
    return results
