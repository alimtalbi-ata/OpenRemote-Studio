"""SQLite local session lifecycle history, no credentials, hosts or command arguments.
Author: Abdelhalim Talbi.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime,timezone

def utcnow():return datetime.now(timezone.utc).isoformat()

class SessionHistory:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY, connection_id TEXT NOT NULL, name TEXT NOT NULL,
                protocol TEXT NOT NULL, pid INTEGER NOT NULL, started_at TEXT NOT NULL,
                finished_at TEXT, exit_code INTEGER,
                UNIQUE(connection_id,pid,started_at))""")
    @contextmanager
    def _db(self):
        """Commit on success, rollback on error, and ALWAYS close the handle."""
        db=sqlite3.connect(str(self.path),timeout=5)
        try:
            db.execute('PRAGMA busy_timeout=5000')
            db.execute('BEGIN')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def started(self,row):
        with self._db() as db:
            db.execute("""INSERT OR IGNORE INTO sessions
                (connection_id,name,protocol,pid,started_at) VALUES (?,?,?,?,?)""",
                (row['connection_id'],row['name'],row['protocol'],row['pid'],row['started_at']))
    def finished(self,row):
        if row.get('status')!='exited' or type(row.get('exit_code')) is not int:return
        with self._db() as db:
            db.execute("""UPDATE sessions SET finished_at=COALESCE(finished_at,?),exit_code=?
                WHERE connection_id=? AND pid=? AND started_at=? AND finished_at IS NULL""",
                (utcnow(),row['exit_code'],row['connection_id'],row['pid'],row['started_at']))
    def recent(self,limit=200):
        if type(limit) is not int or not 1<=limit<=1000:raise ValueError('Limite invalide')
        with self._db() as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute("""SELECT connection_id,name,protocol,pid,started_at,finished_at,exit_code
                FROM sessions ORDER BY id DESC LIMIT ?""",(limit,))]

    def statistics(self,limit=10000):
        """Per-connection observed process outcomes; unobserved != successful."""
        if type(limit) is not int or not 1<=limit<=100000:
            raise ValueError('Limite statistique invalide')
        with self._db() as db:
            db.row_factory=sqlite3.Row
            rows=db.execute("""SELECT connection_id,name,protocol,finished_at,exit_code
                FROM sessions ORDER BY id DESC LIMIT ?""",(limit,)).fetchall()
        result={}
        for r in rows:
            key=r['connection_id']
            item=result.setdefault(key,{'connection_id':key,'name':r['name'],
                'protocol':r['protocol'],'attempts':0,'observed':0,'success':0,
                'failed':0,'unobserved':0})
            item['attempts']+=1
            if r['finished_at'] is None or r['exit_code'] is None:
                item['unobserved']+=1
            else:
                item['observed']+=1
                if r['exit_code']==0:item['success']+=1
                else:item['failed']+=1
        return sorted(result.values(),key=lambda x:(-x['failed'],-x['attempts'],x['name']))
