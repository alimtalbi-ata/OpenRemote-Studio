"""Validated launch planning. Author: Abdelhalim Talbi."""
from access_preflight import inspect_access
from urllib.parse import urlsplit
from connection_policy import connection_route
from gateways import host as valid_host, port as valid_port, ssh_jump_args

def build_launch_plan(c,route=None,which=None,platform=None):
    p=c['protocol']
    if p not in ('SSH','SFTP','RDP','VNC','WEB'):raise ValueError('Protocole inconnu')
    r=connection_route(p,route)
    target=c.get('host','')
    if p=='WEB':
        if not target or not isinstance(target,str):raise ValueError('URL manquante')
        url=target if '://' in target else 'https://'+target
        parts=urlsplit(url)
        if (parts.scheme not in ('https','http') or not parts.hostname or parts.username
            or parts.password or parts.fragment or any(ch.isspace() for ch in target)):
            raise ValueError('URL WEB invalide ou dangereuse')
        try:_=parts.port
        except ValueError:raise ValueError('Port URL WEB invalide')
        check=inspect_access(c,r,which=which,platform=platform)
        return {'ready':check['ready'],'args':None,'rdp':False,'issues':check['issues'],'warnings':check['warnings']}
    valid_host(target)
    port=c.get('port','');user=c.get('user','')
    if not isinstance(user,str) or any(x in user for x in ('\r','\n','\x00')):raise ValueError('Utilisateur invalide')
    if p in ('SSH','SFTP') and (user.startswith('-') or any(x in user for x in '@:/\\ ')):
        raise ValueError('Utilisateur SSH invalide')
    check=inspect_access(c,r,which=which,platform=platform)
    if p=='RDP':
        valid_port(port,3389);args=None
    elif p=='VNC':
        args=['vncviewer',target+(('::'+str(valid_port(port,5900))) if port else '')]
    else:
        resolved=str(valid_port(port,22));endpoint=(user+'@' if user else '')+target
        if p=='SFTP':args=['sftp']+ssh_jump_args(r)+(['-P',resolved] if port else [])+[endpoint]
        else:args=['ssh','-o','StrictHostKeyChecking=yes']+ssh_jump_args(r)+(['-p',resolved] if port else [])+['--',endpoint]
    return {'ready':check['ready'],'args':args,'rdp':p=='RDP','issues':check['issues'],'warnings':check['warnings']}
