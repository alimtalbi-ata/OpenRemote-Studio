"""OpenRemote Studio domain and storage. Author: Abdelhalim Talbi."""
import json, os, re, tempfile, uuid
from pathlib import Path
PROTOCOLS = ('SSH','RDP','SFTP','WEB','VNC')
HOST = re.compile(r'^[A-Za-z0-9][A-Za-z0-9.:-]{0,252}$')

def validate(entry):
    if not isinstance(entry, dict):
        raise ValueError('Connexion invalide : objet JSON attendu')
    entry = {k: ('' if entry.get(k) is None else str(entry.get(k)).strip()) for k in ('id','name','host','protocol','user','group','port','tags')}
    entry['protocol'] = entry['protocol'].upper()
    if not entry['name'] or len(entry['name']) > 150: raise ValueError('Nom requis (150 caractères maximum)')
    if entry['protocol'] not in PROTOCOLS: raise ValueError('Protocole inconnu')
    if entry['protocol'] == 'WEB':
        from urllib.parse import urlsplit
        url = entry['host'] if '://' in entry['host'] else 'https://' + entry['host']
        parts = urlsplit(url)
        if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password: raise ValueError('URL Web non valide')
    elif not HOST.fullmatch(entry['host']) or entry['host'].startswith('-'): raise ValueError('Hôte invalide')
    if entry['port'] and not (entry['port'].isdigit() and 1 <= int(entry['port']) <= 65535): raise ValueError('Port invalide')
    if any(c in entry['user'] for c in '\r\n\x00'): raise ValueError('Utilisateur invalide')
    if not isinstance(entry['name'], str) or any(ord(c)<32 for c in entry['name']):
        raise ValueError('Nom avec caractères de contrôle')
    if entry['protocol'] == 'WEB':
        from urllib.parse import urlsplit
        parts = urlsplit(entry['host'] if '://' in entry['host'] else 'https://' + entry['host'])
        if parts.fragment or any(c.isspace() for c in entry['host']):
            raise ValueError('URL Web invalide')
    entry['id'] = entry['id'] or str(uuid.uuid4())
    return entry

class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.items = self.read()
    def read(self):
        if not self.path.exists(): return []
        raw = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(raw, list): raise ValueError('Format de registre invalide')
        items = [validate(x) for x in raw]
        ids = [x['id'] for x in items]
        if len(ids) != len(set(ids)):
            raise ValueError('Identifiants de connexions dupliqués')
        return items
    def _snapshot_for_save(self):
        """Return a validated snapshot. Subclasses may override for their schema."""
        if type(self) is not Store:
            return self.items
        validated = [validate(item) for item in self.items]
        ids = [item['id'] for item in validated]
        if len(ids) != len(set(ids)):
            raise ValueError('Identifiants de connexions dupliqués')
        return validated

    def save(self):
        # Validate the complete snapshot before creating or replacing any file.
        # A caller must never persist malformed or duplicate connection records.
        validated = self._snapshot_for_save()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.connections-', suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(validated, f, indent=2, ensure_ascii=False)
                f.flush(); os.fsync(f.fileno())
            if os.name != 'nt':
                os.chmod(temp, 0o600)
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp): os.unlink(temp)
    def upsert(self, item):
        item = validate(item)
        old = self.items
        self.items = [x for x in old if x['id'] != item['id']] + [item]
        try: self.save()
        except Exception:
            self.items = old
            raise
    def remove(self, item_id):
        old = self.items
        self.items = [x for x in old if x['id'] != item_id]
        try: self.save()
        except Exception:
            self.items = old
            raise
    def import_json(self, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data, list): raise ValueError('Import: tableau JSON attendu')
        known = {x['id'] for x in self.items}
        additions = []
        for raw in data:
            item = validate(raw)
            if item['id'] in known: item['id'] = str(uuid.uuid4())
            known.add(item['id']); additions.append(item)
        old = self.items
        self.items = old + additions
        try: self.save()
        except Exception:
            self.items = old
            raise
        return len(additions)
