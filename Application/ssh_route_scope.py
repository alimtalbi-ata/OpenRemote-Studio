"""Opt-in pseudonymous SSH route grouping; author Abdelhalim Talbi."""
import hashlib
import hmac
import re

TOKEN_RE=re.compile(r"^[a-f0-9]{64}$")

def route_token(route_descriptor, secret):
    """Return keyed fingerprint; never persist the descriptor or secret.

    Descriptor must be a stable, user-chosen canonical route identifier.
    The secret must be random and held outside the history database.
    """
    if not isinstance(route_descriptor,str) or not 1<=len(route_descriptor)<=512 or not route_descriptor.isprintable():
        raise ValueError('Identifiant de parcours invalide')
    if not isinstance(secret,bytes) or len(secret)<32:
        raise ValueError('Clé de pseudonymisation trop courte')
    return hmac.new(secret,b'openremote.route.v1\0'+route_descriptor.encode('utf-8'),hashlib.sha256).hexdigest()

def validate_token(token):
    if not isinstance(token,str) or TOKEN_RE.fullmatch(token) is None:
        raise ValueError('Jeton de parcours invalide')
    return token
