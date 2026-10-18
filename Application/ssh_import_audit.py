"""Bounded, anonymized import audit views and authenticated exports.
Author: Abdelhalim Talbi.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone

FIELDS=('imported_at','total','inserted','duplicates','conflicts')

def validate_rows(rows):
    if not isinstance(rows,list) or len(rows)>100: raise ValueError('Journal invalide')
    result=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!=set(FIELDS): raise ValueError('Entrée invalide')
        if any(type(row[k]) is not int or row[k]<0 for k in FIELDS): raise ValueError('Compteur invalide')
        if row['inserted']+row['duplicates']!=row['total'] or row['conflicts']>row['inserted']:
            raise ValueError('Compteurs incohérents')
        result.append({k:row[k] for k in FIELDS})
    return result

def filter_rows(rows, *, since=None, until=None, conflicts_only=False, limit=100):
    clean=validate_rows(rows)
    if type(limit) is not int or not 1<=limit<=100: raise ValueError('Limite invalide')
    for x in (since,until):
        if x is not None and (type(x) is not int or x<0): raise ValueError('Date invalide')
    if since is not None and until is not None and since>until: raise ValueError('Période invalide')
    if type(conflicts_only) is not bool: raise ValueError('Filtre invalide')
    return [r for r in clean if (since is None or r['imported_at']>=since) and
            (until is None or r['imported_at']<=until) and
            (not conflicts_only or r['conflicts']>0)][:limit]

def summary(rows):
    clean=validate_rows(rows)
    return {'operations':len(clean),**{k:sum(r[k] for r in clean) for k in FIELDS if k!='imported_at'}}

def _canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')

def export_signed(rows,key):
    if not isinstance(key,bytes) or len(key)<16: raise ValueError('Clé externe invalide')
    payload={'schema':'openremote.ssh-import-audit.v1','rows':validate_rows(rows)}
    return {'payload':payload,'hmac_sha256':hmac.new(key,_canonical(payload),hashlib.sha256).hexdigest()}

def verify_signed(envelope,key):
    if not isinstance(key,bytes) or len(key)<16: raise ValueError('Clé externe invalide')
    if not isinstance(envelope,dict) or set(envelope)!={'payload','hmac_sha256'}: raise ValueError('Enveloppe invalide')
    payload=envelope['payload']; signature=envelope['hmac_sha256']
    if not isinstance(payload,dict) or set(payload)!={'schema','rows'} or payload['schema']!='openremote.ssh-import-audit.v1': raise ValueError('Schéma invalide')
    if not isinstance(signature,str) or len(signature)!=64: raise ValueError('Signature invalide')
    rows=validate_rows(payload['rows'])
    expected=hmac.new(key,_canonical(payload),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature): raise ValueError('Signature incorrecte')
    return rows
