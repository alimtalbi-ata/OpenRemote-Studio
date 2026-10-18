"""Explicit-consent SSH chain validation, no shell, no remote commands.
Author: Abdelhalim Talbi.
"""
from gateways import host as valid_host, port as valid_port
from ssh_path_editor import hops_to_route
from time import monotonic


def probe(hops, target, port=22, user='', factory=None, consent=False, cancelled=None, on_event=None, connect_timeout=10, clock=None):
    """Authenticate each hop and target with strict known_hosts; return redacted stages."""
    if type(connect_timeout) is not int or not 2<=connect_timeout<=20:
        raise ValueError("Délai SSH invalide")
    if consent is not True:
        raise PermissionError('Consentement explicite requis')
    route=hops_to_route(hops)
    endpoint={'host':valid_host(target),'port':valid_port(port,22),'user':str(user or '')}
    if any(x in endpoint['user'] for x in ('\n','\r','\x00')) or len(endpoint['user'])>128:
        raise ValueError('Utilisateur cible invalide')
    events=[]
    timer=clock or monotonic
    starts={}
    def stage(name,state):
        # Fixed status vocabulary, never log remote exceptions, addresses or credentials.
        safe_state=state if state in ('starting','ok','failed') else 'failed'
        if name.startswith('bastion_') and name.endswith('_connect'):
            suffix=name[len('bastion_'):-len('_connect')]
            label='Bastion '+suffix if suffix.isdigit() else 'Bastion principal'
        elif name=='bastion_connect':label='Bastion principal'
        elif name=='target_connect':label='Serveur cible'
        else:label='Étape SSH'
        now=timer()
        event={'step':label,'state':safe_state}
        if safe_state=='starting':starts[label]=now
        elif label in starts:
            event['duration_ms']=max(0,min(3600000,round((now-starts.pop(label))*1000)))
        events.append(event)
        if on_event is not None:on_event(dict(event))
    if factory is None:
        from ssh_route_client import RoutedSshClient
        factory=RoutedSshClient
    client=None
    try:
        if cancelled is not None and cancelled.is_set():
            return {'status':'cancelled','events':events,'message':'Diagnostic SSH annulé avant connexion.'}
        client=factory(endpoint,route,on_stage=stage,keepalive=0,**({'connect_timeout':connect_timeout} if connect_timeout!=10 else {}),**({'cancelled':cancelled} if cancelled is not None else {}))
        client.connect()
        if cancelled is not None and cancelled.is_set():
            return {'status':'cancelled','events':events,'message':'Diagnostic SSH annulé ; aucune commande distante exécutée.'}
        return {'status':'authenticated','events':events,
                'message':'Authentification SSH de chaque saut et de la cible réussie ; aucun shell ni commande distante exécutés.'}
    except InterruptedError:
        return {'status':'cancelled','events':events,'message':'Diagnostic SSH annulé ; connexions ouvertes fermées.'}
    except Exception:
        return {'status':'failed','events':events,
                'message':'Échec de connexion SSH : vérifier le saut signalé, les clés, known_hosts et les ACL. Aucun détail sensible affiché.'}
    finally:
        if client is not None:client.close()
