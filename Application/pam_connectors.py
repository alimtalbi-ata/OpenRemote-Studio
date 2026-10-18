"""Fail-closed PAM connector contract, no live provider implementation.
Author: Abdelhalim Talbi.
"""
from dataclasses import dataclass
from pam_refs import parse_reference
from pam_profiles import validate_profile

@dataclass(frozen=True)
class ConnectorCapabilities:
    provider: str
    authentication: bool = False
    authorization: bool = False
    session_broker: bool = False
    credential_injection: bool = False

class PamConnector:
    """Contract for future audited connectors; no default implementation."""
    def __init__(self, profile):
        self.profile=validate_profile(profile)
    @property
    def capabilities(self):
        return ConnectorCapabilities(self.profile['provider'])
    def authenticate(self, context):
        raise NotImplementedError('Connecteur PAM non implémenté')
    def authorize(self, principal, resource):
        raise NotImplementedError('Autorisation PAM non implémentée')
    def open_session(self, grant, target):
        raise NotImplementedError('Session PAM non implémentée')

class ConnectorRegistry:
    """No dynamic plugins, implicit fallbacks or external network calls."""
    def __init__(self, profiles=()):
        self.profiles=tuple(validate_profile(p) for p in profiles)
    def inspect(self, reference):
        ref=parse_reference(reference)
        if ref is None:
            return {'pam_required':False,'authorized':False,'ready':True,
                    'profiles':[],'reason':'Connexion sans PAM'}
        matches=[p['name'] for p in self.profiles if p['provider']==ref.provider]
        return {'pam_required':True,'authorized':False,'ready':False,
                'profiles':sorted(matches,key=str.casefold),
                'reason':'Connecteur PAM non implémenté : ouverture de session interdite'}
    def open_session(self, reference, target):
        status=self.inspect(reference)
        if not status['pam_required']:
            raise PermissionError('Aucune demande PAM : broker interdit')
        raise PermissionError(status['reason'])
