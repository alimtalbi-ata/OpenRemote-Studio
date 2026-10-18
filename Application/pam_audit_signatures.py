"""Detached Ed25519 signatures for simulated PAM audit reports.
Private keys are supplied by the caller, never generated or persisted here.
Author: Abdelhalim Talbi.
"""
import base64, json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from pam_lab_reports import canonical,verify_report

FORMAT='openremote-pam-lab-signature-v1'

def sign_report(report,private_key_pem):
    if not verify_report(report):raise ValueError('Audit invalide : signature refusée')
    key=serialization.load_pem_private_key(private_key_pem,password=None)
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('Clé Ed25519 privée requise')
    public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    return {'format':FORMAT,'algorithm':'Ed25519',
            'public_key_fingerprint':__import__('hashlib').sha256(public).hexdigest(),
            'signature':base64.b64encode(key.sign(canonical(report))).decode('ascii')}

def verify_signed_report(report,signature,public_key_pem):
    if not verify_report(report) or not isinstance(signature,dict):return False
    if set(signature)!={'format','algorithm','public_key_fingerprint','signature'}:return False
    if signature['format']!=FORMAT or signature['algorithm']!='Ed25519':return False
    try:
        key=serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key,Ed25519PublicKey):return False
        raw=key.public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        if signature['public_key_fingerprint']!=__import__('hashlib').sha256(raw).hexdigest():return False
        encoded=signature['signature']
        if not isinstance(encoded,str) or len(encoded)>128:return False
        sig=base64.b64decode(encoded,validate=True)
        key.verify(sig,canonical(report))
        return True
    except (InvalidSignature,ValueError,TypeError,KeyError):return False

def verify_signed_files(report_path,signature_path,public_key_path,max_bytes=10_000_000):
    def read_bounded(path,limit):
        p=Path(path)
        if p.stat().st_size>limit:raise ValueError('Fichier trop volumineux')
        with p.open('rb') as f:data=f.read(limit+1)
        if len(data)>limit:raise ValueError('Fichier trop volumineux')
        return data
    try:
        report=json.loads(read_bounded(report_path,max_bytes))
        signature=json.loads(read_bounded(signature_path,4096))
        key=read_bounded(public_key_path,8192)
    except (UnicodeError,json.JSONDecodeError) as exc:raise ValueError('Fichier de signature ou audit invalide') from exc
    return verify_signed_report(report,signature,key)
