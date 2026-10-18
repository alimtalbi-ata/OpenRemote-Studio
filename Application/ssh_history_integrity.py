"""Authenticated, anonymized SSH diagnostic history exports. Author: Abdelhalim Talbi."""
import hashlib
import hmac
import json
from ssh_diagnostic_history import normalize

DOMAIN = b"openremote.history.export.v1\0"

def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")

def _key(key):
    if type(key) is not bytes or len(key) < 32:
        raise ValueError("Cle HMAC externe de 32 octets minimum requise")
    return key

def create_export(records, key):
    """Create a signed portable export; never include route tokens or raw endpoint data."""
    _key(key)
    if not isinstance(records, list) or len(records) > 200:
        raise ValueError("Historique invalide")
    clean = []
    for row in records:
        if not isinstance(row, dict) or type(row.get('recorded_at')) is not int or row['recorded_at'] < 0:
            raise ValueError("Horodatage invalide")
        clean.append({'recorded_at': row['recorded_at'], 'report': normalize(row['report'])})
    payload = {'schema': 'openremote.ssh-history-export.v1', 'records': clean}
    digest = hmac.new(key, DOMAIN + _canonical(payload), hashlib.sha256).hexdigest()
    return {'payload': payload, 'hmac_sha256': digest}

def verify_export(document, key):
    """Verify signature, strict schema and canonical normalized content before returning records."""
    _key(key)
    if not isinstance(document, dict) or set(document) != {'payload', 'hmac_sha256'}:
        raise ValueError('Enveloppe invalide')
    payload = document['payload']
    digest = document['hmac_sha256']
    if not isinstance(payload, dict) or set(payload) != {'schema', 'records'} or payload['schema'] != 'openremote.ssh-history-export.v1':
        raise ValueError('Schema invalide')
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Signature invalide')
    expected = hmac.new(key, DOMAIN + _canonical(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest):
        raise ValueError('Integrite du rapport non verifiee')
    records = payload['records']
    if not isinstance(records, list) or len(records) > 200:
        raise ValueError('Nombre de rapports invalide')
    for row in records:
        if not isinstance(row, dict) or set(row) != {'recorded_at', 'report'} or type(row['recorded_at']) is not int or row['recorded_at'] < 0:
            raise ValueError('Enregistrement invalide')
        if normalize(row['report']) != row['report']:
            raise ValueError('Contenu non canonique')
    return records
