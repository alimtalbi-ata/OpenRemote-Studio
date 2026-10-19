"""SQLite transfer audit journal. No secrets; never automatically replays jobs.
Author: Abdelhalim Talbi.
"""
import sqlite3
from datetime import datetime,timezone
from pathlib import Path

KINDS=frozenset(('upload','download','resume_download'))
STATES=frozenset(('waiting','running','done','failed','cancelled','interrupted'))

class TransferJournal:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(self.path),timeout=10)
        self.db.execute('PRAGMA busy_timeout=10000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute("""CREATE TABLE IF NOT EXISTS transfers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            remote_path TEXT NOT NULL,
            local_path TEXT NOT NULL,
            state TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        self.db.commit()
        self.recover()
    def recover(self):
        with self.db:
            self.db.execute("UPDATE transfers SET state='interrupted', updated_at=? WHERE state IN ('waiting','running')",
                            (self.now(),))
    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()
    def add(self,connection_id,operation,remote_path,local_path):
        if operation not in KINDS:raise ValueError('Opération non journalisable')
        if not connection_id or not remote_path:raise ValueError('Transfert incomplet')
        stamp=self.now()
        with self.db:
            cursor=self.db.execute("""INSERT INTO transfers(connection_id,operation,remote_path,local_path,state,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?)""",(str(connection_id),operation,str(remote_path),str(local_path or ''),'waiting',stamp,stamp))
        return cursor.lastrowid
    def update(self,transfer_id,state,progress=None):
        if state not in STATES:raise ValueError('État invalide')
        if progress is not None and (not isinstance(progress,int) or not 0<=progress<=100):
            raise ValueError('Progression invalide')
        # Terminal outcomes are immutable. Use a guarded SQL update so competing
        # callbacks cannot overwrite a completed or cancelled transfer.
        with self.db:
            cursor=self.db.execute("""UPDATE transfers
                SET state=?,progress=COALESCE(?,progress),updated_at=?
                WHERE id=? AND state IN ('waiting','running')
                  AND (? IS NULL OR progress<=?)""",
                (state,progress,self.now(),transfer_id,progress,progress))
            if cursor.rowcount!=1:
                row=self.db.execute("SELECT state,progress FROM transfers WHERE id=?",
                                    (transfer_id,)).fetchone()
                if row is None:raise KeyError(transfer_id)
                raise ValueError('Transfert terminé ou progression régressive')
    def recent(self,limit=50):
        if not isinstance(limit,int) or not 1<=limit<=500:raise ValueError('Limite invalide')
        return self.db.execute("""SELECT id,connection_id,operation,remote_path,local_path,state,progress
          FROM transfers ORDER BY id DESC LIMIT ?""",(limit,)).fetchall()
    def search(self, state=None, connection_id=None, limit=100):
        """Read-only, parameterized journal filtering; newest entries first."""
        if state is not None and state not in STATES:
            raise ValueError('État invalide')
        if not isinstance(limit,int) or not 1<=limit<=500:
            raise ValueError('Limite invalide')
        clauses=[]; params=[]
        if state is not None:
            clauses.append('state=?');params.append(state)
        if connection_id is not None:
            clauses.append('connection_id=?');params.append(str(connection_id))
        where=(' WHERE '+' AND '.join(clauses)) if clauses else ''
        return self.db.execute('SELECT id,connection_id,operation,remote_path,local_path,state,progress,updated_at FROM transfers'+where+' ORDER BY id DESC LIMIT ?',(*params,limit)).fetchall()

    def close(self):
        self.db.close()
