"""Local non-secret PAM provider profiles; never stores tokens or credentials.
Author: Abdelhalim Talbi.
"""
from urllib.parse import urlsplit
from core import Store
from pam_refs import PROVIDERS

def validate_profile(raw):
    if not isinstance(raw,dict):raise ValueError('Profil PAM invalide')
    name=raw.get('name','')
    provider=raw.get('provider','')
    endpoint=raw.get('endpoint','')
    if not isinstance(name,str) or not name.strip() or len(name)>80 or any(ord(c)<32 for c in name):
        raise ValueError('Nom de profil invalide')
    if provider not in PROVIDERS:raise ValueError('Fournisseur PAM inconnu')
    if not isinstance(endpoint,str) or len(endpoint)>512:
        raise ValueError('Point d’accès PAM invalide')
    parsed=urlsplit(endpoint)
    if (parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password
        or parsed.fragment or parsed.query or any(c.isspace() for c in endpoint)
        or parsed.port is not None and not 1<=parsed.port<=65535):
        raise ValueError('URL HTTPS PAM sans identifiants ni paramètres requise')
    return {'name':name.strip(),'provider':provider,'endpoint':endpoint.rstrip('/')}

class PamProfileStore(Store):
    def read(self):
        if not self.path.exists():return []
        import json
        raw=json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(raw,list):raise ValueError('Format de profils PAM invalide')
        profiles=[validate_profile(x) for x in raw]
        names=[x['name'].casefold() for x in profiles]
        if len(names)!=len(set(names)):raise ValueError('Profils PAM dupliqués')
        return profiles
    def set_profile(self,raw):
        value=validate_profile(raw)
        old=self.items
        self.items=[x for x in old if x['name'].casefold()!=value['name'].casefold()]+[value]
        try:self.save()
        except Exception:
            self.items=old
            raise
    def remove_profile(self,name):
        old=self.items
        self.items=[x for x in old if x['name']!=name]
        try:self.save()
        except Exception:
            self.items=old
            raise
