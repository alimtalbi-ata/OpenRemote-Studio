"""Isolated PAM simulation: policy, one-use grants, expiry, audit.
No network access, no credentials, no real session launch.
Author: Abdelhalim Talbi.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from secrets import token_urlsafe
from pam_refs import parse_reference

@dataclass(frozen=True)
class SimulatedGrant:
    grant_id: str
    principal: str
    reference: str
    target: str
    expires_at: float

class SimulatedPamBroker:
    def __init__(self, clock, ttl_seconds=60):
        if not callable(clock):raise TypeError('Horloge requise')
        if not isinstance(ttl_seconds,int) or not 1<=ttl_seconds<=3600:
            raise ValueError('Durée de validité invalide')
        self._clock=clock
        self._ttl=ttl_seconds
        self._grants={}
        self._events=[]
    def _event(self,action,decision,principal='',reference='',target='',reason=''):
        self._events.append({'timestamp':datetime.fromtimestamp(self._clock(),timezone.utc).isoformat(),
            'action':action,'decision':decision,'principal':principal,
            'reference':reference,'target':target,'reason':reason})
    @staticmethod
    def _valid_field(value):
        return isinstance(value,str) and 0<len(value)<=256 and value.strip()==value and not any(ord(c)<32 for c in value)
    def authorize(self,principal,reference,target,approved=False):
        if not all(self._valid_field(v) for v in (principal,reference,target)):
            self._event('authorize','DENY',reason='Invalid input')
            raise PermissionError('Paramètres invalides')
        try:parse_reference(reference)
        except ValueError:
            self._event('authorize','DENY',principal,reason='Invalid PAM reference')
            raise PermissionError('Référence PAM invalide') from None
        if approved is not True:
            self._event('authorize','DENY',principal,reference,target,'Explicit approval required')
            raise PermissionError('Approbation explicite requise')
        grant=SimulatedGrant(token_urlsafe(24),principal,reference,target,self._clock()+self._ttl)
        self._grants[grant.grant_id]=grant
        self._event('authorize','ALLOW_SIMULATION',principal,reference,target)
        return grant
    def open_session(self,grant_id,principal,reference,target):
        grant=self._grants.pop(grant_id,None) if isinstance(grant_id,str) else None
        if grant is None:
            self._event('session','DENY',reason='Missing or consumed grant')
            raise PermissionError('Autorisation absente ou déjà utilisée')
        if self._clock()>=grant.expires_at:
            self._event('session','DENY',reason='Expired grant')
            raise PermissionError('Autorisation expirée')
        if (principal,reference,target)!=(grant.principal,grant.reference,grant.target):
            self._event('session','DENY',reason='Grant binding mismatch')
            raise PermissionError('Contexte de session différent')
        self._event('session','SIMULATED_ONLY',principal,reference,target)
        return {'simulated':True,'real_session':False,'target':target,
                'message':'Simulation uniquement : aucune session ouverte'}
    def audit(self):
        return tuple(dict(event) for event in self._events)
