"""Shared strict SSH route for SFTP; Author: Abdelhalim Talbi."""
from gateways import validate_route, parse_jump_chain, host as valid_host, port as valid_port

class RoutedSshClient:
    """Own all hop clients/channels; close in reverse order even after partial failure."""
    def __init__(self, target, route=None, paramiko_module=None, on_stage=None, keepalive=0, cancelled=None, connect_timeout=10):
        if paramiko_module is None:
            import paramiko as paramiko_module
        self.paramiko=paramiko_module
        self.route=validate_route(route)
        if self.route['mode'] not in ('','direct','ssh_jump'):
            raise ValueError('Route incompatible SSH/SFTP')
        self.target=(valid_host(target['host']),valid_port(target.get('port'),22),str(target.get('user') or ''))
        if not isinstance(keepalive,int) or isinstance(keepalive,bool) or keepalive not in (0,*range(10,301)):
            raise ValueError('Keepalive invalide')
        if type(connect_timeout) is not int or not 2<=connect_timeout<=20:
            raise ValueError("Délai de connexion SSH invalide (2–20 s)")
        self.connect_timeout=connect_timeout
        self.keepalive=keepalive
        self.on_stage=on_stage
        self.cancelled=cancelled
        self.clients=[];self.channels=[]

    def connect(self):
        if self.clients:raise RuntimeError('Connexion déjà utilisée')
        hops=[]
        if self.route['mode']=='ssh_jump':
            r=self.route
            hops=[{'host':r['jump_host'],'port':int(r['jump_port']),'user':r['jump_user']}]+parse_jump_chain(r['jump_chain'])
        hops.append(dict(zip(('host','port','user'),self.target)))
        sock=None
        try:
            for index,hop in enumerate(hops):
                if self.cancelled is not None and self.cancelled.is_set():
                    raise InterruptedError('Connexion annulée')
                stage=('bastion_connect' if index==0 else f'bastion_{index+1}_connect') if index<len(hops)-1 else 'target_connect'
                if self.on_stage:self.on_stage(stage,'starting')
                client=self.paramiko.SSHClient()
                self.clients.append(client)
                client.load_system_host_keys()
                client.set_missing_host_key_policy(self.paramiko.RejectPolicy())
                if index:
                    transport=self.clients[-2].get_transport()
                    if transport is None or not transport.is_active():raise ConnectionError('Transport rebond inactif')
                    sock=transport.open_channel('direct-tcpip',(hop['host'],hop['port']),('127.0.0.1',0),timeout=self.connect_timeout)
                    if sock is None:raise ConnectionError('Tunnel SSH indisponible')
                    self.channels.append(sock)
                client.connect(hostname=hop['host'],port=hop['port'],username=hop['user'] or None,
                    timeout=self.connect_timeout,auth_timeout=self.connect_timeout,banner_timeout=self.connect_timeout,allow_agent=True,look_for_keys=True,
                    **({'sock':sock} if sock is not None else {}))
                transport=client.get_transport()
                if transport is None or not transport.is_active():raise ConnectionError('Transport SSH inactif')
                if self.keepalive:transport.set_keepalive(self.keepalive)
                if self.on_stage:self.on_stage(stage,'ok')
            return self
        except BaseException:
            if self.on_stage and 'stage' in locals():self.on_stage(stage,'failed')
            self.close()
            raise

    @property
    def target_client(self):
        if not self.clients:raise RuntimeError('Connexion absente')
        return self.clients[-1]

    def transports_active(self):
        return bool(self.clients) and all(
            c.get_transport() is not None and c.get_transport().is_active()
            for c in self.clients)

    def open_sftp(self):
        if not self.clients:raise RuntimeError('Connexion absente')
        return self.clients[-1].open_sftp()

    def close(self):
        for client in reversed(self.clients):
            try:client.close()
            except Exception:pass
        for channel in reversed(self.channels):
            try:channel.close()
            except Exception:pass
        self.clients.clear();self.channels.clear()
