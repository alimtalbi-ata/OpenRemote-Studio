"""Bounded, metadata-only probe history. Author: Abdelhalim Talbi."""
import sqlite3
from contextlib import closing
from pathlib import Path

ALLOWED = {'ok', 'failed', 'unknown'}
class ProbeHistory:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS probes (
                id INTEGER PRIMARY KEY, connection_id TEXT NOT NULL,
                kind TEXT NOT NULL, outcome TEXT NOT NULL,
                observed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )""")
            db.execute('CREATE INDEX IF NOT EXISTS idx_probes_conn ON probes(connection_id, id DESC)')
            db.commit()
    def add(self, connection_id, kind, outcome):
        if not isinstance(connection_id,str) or not connection_id or len(connection_id)>128:
            raise ValueError('Identifiant de connexion invalide')
        if kind not in {'ssh_jump','tcp_local'} or outcome not in ALLOWED:
            raise ValueError('Diagnostic invalide')
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.execute('INSERT INTO probes(connection_id,kind,outcome) VALUES(?,?,?)', (connection_id,kind,outcome))
            db.commit()
    def recent(self, connection_id=None, limit=100):
        if not isinstance(limit,int) or not 1<=limit<=500:raise ValueError('Limite invalide')
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            if connection_id is None:
                rows=db.execute('SELECT connection_id,kind,outcome,observed_at FROM probes ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
            else:
                rows=db.execute('SELECT connection_id,kind,outcome,observed_at FROM probes WHERE connection_id=? ORDER BY id DESC LIMIT ?', (connection_id,limit)).fetchall()
        return rows

def classify_ssh_result(message):
    """No raw stderr is persisted; an SSH -W exit 0 is still indeterminate."""
    value=str(message).lower()
    if any(s in value for s in ('refused','denied','échec','error','failed','impossible','unreachable','introuvable')):
        return 'failed'
    return 'unknown'
