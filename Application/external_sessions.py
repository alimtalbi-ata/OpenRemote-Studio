"""In-memory external client registry; no process termination or credential capture.
Author: Abdelhalim Talbi.
"""
from dataclasses import dataclass
from datetime import datetime,timezone

@dataclass
class ExternalSession:
    connection_id: str
    name: str
    protocol: str
    pid: int
    started_at: str
    process: object

class ExternalSessionRegistry:
    def __init__(self,history=None):
        self._sessions=[];self.history=history;self.history_errors=[];self._reconciled=set()
    def register(self,connection,process):
        pid=getattr(process,'pid',None)
        if not isinstance(pid,int) or pid<=0:raise ValueError('PID invalide')
        session=ExternalSession(str(connection['id']),str(connection['name']),
            str(connection['protocol']),pid,datetime.now(timezone.utc).isoformat(),process)
        self._sessions.append(session)
        if self.history is not None:
            try:self.history.started({'connection_id':session.connection_id,'name':session.name,
                'protocol':session.protocol,'pid':session.pid,'started_at':session.started_at})
            except (OSError,ValueError,Exception) as exc:
                self.history_errors.append(str(exc))
        return session
    def snapshot(self):
        rows=[]
        for session in self._sessions:
            try:code=session.process.poll()
            except (OSError,ValueError):code=None;inspection_failed=True
            else:inspection_failed=False
            rows.append({'connection_id':session.connection_id,'name':session.name,
                'protocol':session.protocol,'pid':session.pid,'started_at':session.started_at,
                'status':'unknown' if inspection_failed else ('running' if code is None else 'exited'),'exit_code':code})
        if self.history is not None:
            for row in rows:
                if row['status']=='exited':
                    key=(row['connection_id'],row['pid'],row['started_at'])
                    if key in self._reconciled:continue
                    try:
                        self.history.finished(row)
                        self._reconciled.add(key)
                    except Exception as exc:self.history_errors.append(str(exc))
        return rows
    def reconnect_candidate(self, connection_id, pid=None):
        """Resolve an exited session by exact identity; reject ambiguous or live siblings.

        A missing PID is deliberately rejected: the caller must use the selected row,
        not an arbitrary recent process belonging to the same connection.
        """
        from session_selection import selected_session
        from session_presentation import selected_reconnect_allowed
        rows = self.snapshot()
        if not selected_reconnect_allowed(rows, connection_id, pid):
            return None
        return selected_session(rows, connection_id, pid)

    def has_running(self,connection_id):
        return any(row['connection_id']==connection_id and row['status'] in ('running','unknown')
                   for row in self.snapshot())

    def clear_exited(self):
        retained=[]
        for s in self._sessions:
            try:alive=s.process.poll() is None
            except (OSError,ValueError):alive=True
            if alive:retained.append(s)
        removed=len(self._sessions)-len(retained)
        self._sessions=retained
        return removed
