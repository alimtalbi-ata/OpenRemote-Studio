"""Consent-only SSH jump TCP path check; no remote shell. Author: Abdelhalim Talbi."""
import subprocess
from gateways import validate_route,host as valid_host,port as valid_port,ssh_jump_args
from network_probe import endpoint

def command(connection,route,timeout=7):
    checked=validate_route(route)
    if checked['mode']!='ssh_jump':raise ValueError('Un rebond SSH est requis')
    if connection.get('protocol') not in ('SSH','SFTP'):raise ValueError('Protocole incompatible')
    target,number=endpoint(connection)
    target=valid_host(target)
    number=valid_port(number,22)
    if not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not 1<=timeout<=15:raise ValueError('Délai invalide')
    jump_user=checked['jump_user']
    jump=(jump_user+'@' if jump_user else '')+checked['jump_host']
    # -W opens a direct TCP channel from the SSH bastion; no remote shell/command.
    return ['ssh','-T','-n','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
            '-o','NumberOfPasswordPrompts=0','-o',f'ConnectTimeout={int(timeout)}',
            '-p',checked['jump_port'],'-W',f'{target}:{number}','--',jump]

def classify(returncode, stderr=b'', timed_out=False):
    """Conservative SSH transport outcome; never equate exit 0 with remote login."""
    if timed_out:
        return {'status':'indeterminate','reachable':False,
                'message':'Délai dépassé : état du canal indéterminé (aucune preuve de succès).'}
    if returncode == 0:
        return {'status':'channel_closed_cleanly','reachable':True,
                'message':'Canal SSH -W terminé avec code 0 ; authentification applicative cible non vérifiée.'}
    # Only stable SSH diagnostic fragments; never surface arbitrary stderr, paths or usernames.
    diagnostic=stderr.decode('utf-8','replace').lower() if isinstance(stderr,bytes) else str(stderr).lower()
    if any(x in diagnostic for x in ('permission denied','authentication failed','host key verification failed','too many authentication failures')):
        status='bastion_auth_or_trust'
        msg='Authentification ou confiance SSH du bastion refusée ; vérifier clés et known_hosts.'
    elif any(x in diagnostic for x in ('administratively prohibited','open failed','connect failed','connection refused','no route to host','network is unreachable')):
        status='target_channel_failed'
        msg='Ouverture du canal vers la cible refusée ou impossible ; vérifier ACL, routage et port depuis le bastion.'
    elif any(x in diagnostic for x in ('could not resolve hostname','name or service not known')):
        status='name_resolution_failed'
        msg='Résolution DNS impossible ; vérifier le nom du bastion ou de la cible.'
    else:
        status='unclassified_failure'
        msg='Échec SSH non classifié ; consulter les journaux locaux sécurisés.'
    return {'status':status,'reachable':False,'message':msg+' (code '+str(returncode)+').'}

def check(connection,route,timeout=7,runner=None):
    args=command(connection,route,timeout)
    run=runner or subprocess.run
    try:
        result=run(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE,timeout=float(timeout)+3,check=False)
    except subprocess.TimeoutExpired:
        return classify(None,timed_out=True)
    except OSError:
        return {'status':'client_unavailable','reachable':False,
                'message':'Impossible de démarrer le client SSH local.'}
    return classify(result.returncode,result.stderr)
