"""Encrypted local secret vault. Author: Abdelhalim Talbi."""
import base64, json, os, tempfile
from pathlib import Path

class Vault:
    def __init__(self, path):
        self.path = Path(path)

    @staticmethod
    def _key(password, salt):
        if not password or len(password) < 12:
            raise ValueError("Phrase secrète : 12 caractères minimum")
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password.encode('utf-8'))

    def save(self, secrets, password):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if not isinstance(secrets, dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in secrets.items()):
            raise ValueError("Le coffre attend un dictionnaire de chaînes")
        salt, nonce = os.urandom(16), os.urandom(12)
        key = self._key(password,salt)
        ciphertext = AESGCM(key).encrypt(nonce,json.dumps(secrets,ensure_ascii=False).encode(),b'OpenRemoteStudioVault-v1')
        payload = {'version':1,'kdf':'scrypt','cipher':'AES-256-GCM','salt':base64.b64encode(salt).decode(),'nonce':base64.b64encode(nonce).decode(),'data':base64.b64encode(ciphertext).decode()}
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix='.vault-',dir=self.path.parent)
        try:
            if os.name != 'nt':os.fchmod(fd,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(payload,f);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def load(self,password):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        data=json.loads(self.path.read_text(encoding='utf-8'))
        if data.get('version')!=1 or data.get('kdf')!='scrypt' or data.get('cipher')!='AES-256-GCM':
            raise ValueError('Format de coffre non pris en charge')
        decode=lambda name:base64.b64decode(data[name],validate=True)
        salt,nonce=decode('salt'),decode('nonce')
        if len(salt)!=16 or len(nonce)!=12:raise ValueError('Paramètres de coffre invalides')
        raw=AESGCM(self._key(password,salt)).decrypt(nonce,decode('data'),b'OpenRemoteStudioVault-v1')
        result=json.loads(raw)
        if not isinstance(result,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in result.items()):raise ValueError('Contenu du coffre invalide')
        return result
