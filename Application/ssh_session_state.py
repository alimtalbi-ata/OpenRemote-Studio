"""Explicit SSH PTY lifecycle and user-safe diagnostic mapping. Abdelhalim Talbi."""
from enum import Enum

class SessionState(str,Enum):
    NEW='new'
    CONNECTING='connecting'
    CONNECTED='connected'
    STOPPING='stopping'
    CLOSED='closed'
    FAILED='failed'

ALLOWED={
    SessionState.NEW:{SessionState.CONNECTING,SessionState.STOPPING},
    SessionState.CONNECTING:{SessionState.CONNECTED,SessionState.STOPPING,SessionState.FAILED},
    SessionState.CONNECTED:{SessionState.STOPPING,SessionState.CLOSED,SessionState.FAILED},
    SessionState.STOPPING:{SessionState.CLOSED},
    SessionState.CLOSED:set(),SessionState.FAILED:{SessionState.CLOSED},
}
class Lifecycle:
    def __init__(self):self.state=SessionState.NEW
    def transition(self,new):
        new=SessionState(new)
        if new==self.state:return False
        if new not in ALLOWED[self.state]:raise ValueError(f'Invalid SSH lifecycle transition: {self.state} -> {new}')
        self.state=new
        return True

def classify_failure(exc):
    """Avoid exposing credentials, hostnames, remote banners or stack traces."""
    name=type(exc).__name__
    if name in ('AuthenticationException','BadAuthenticationType','PasswordRequiredException'):
        return 'Authentification SSH refusée : vérifier les clés ou l’agent.'
    if name in ('BadHostKeyException','SSHException'):
        return 'Vérification SSH impossible : contrôler known_hosts et la négociation.'
    if name in ('TimeoutError','socket.timeout'):
        return 'Délai de connexion SSH dépassé.'
    if name in ('ConnectionRefusedError','ConnectionResetError','BrokenPipeError','EOFError'):
        return 'Connexion SSH interrompue ou refusée.'
    if name in ('OSError','gaierror'):
        return 'Erreur réseau SSH : vérifier la connectivité et le DNS.'
    return 'Session SSH indisponible : '+name[:80]
