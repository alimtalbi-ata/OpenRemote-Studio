
"""Deterministic per-tab transfer queue, independent of Qt.
Author: Abdelhalim Talbi.
"""
from collections import deque

class TransferQueue:
    def __init__(self):
        self.pending=deque()
        self.active=None
        self.history=[]
        self._next_id=0
    def submit(self,job):
        self._next_id+=1
        entry={"id":self._next_id,"job":job,"state":"waiting","progress":0}
        self.pending.append(entry)
        return entry
    def start_next(self):
        if self.active is not None or not self.pending:return None
        entry=self.pending.popleft()
        entry["state"]="running"
        self.active=entry
        return entry
    def progress(self,entry,value):
        if self.active is not entry:return
        entry["progress"]=max(0,min(100,int(value)))
    def complete(self,entry,ok):
        if self.active is not entry:raise ValueError("Opération non active")
        entry["state"]="done" if ok else "failed"
        self.history.append(entry)
        self.active=None
    def cancel_pending(self):
        while self.pending:
            entry=self.pending.popleft()
            entry["state"]="cancelled"
            self.history.append(entry)
    def cancel_active(self):
        if self.active is not None:self.active["job"].cancel()
