"""Atomic workspace preferences; never contains credentials. Author: Abdelhalim Talbi."""
import json, os, tempfile
from pathlib import Path

class Workspace:
    def __init__(self,path):
        self.path=Path(path)
        self.data=self.load()
    def load(self):
        if not self.path.exists(): return {"favorites":[],"recent":[],"tool_favorites":[]}
        raw=json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw,dict): raise ValueError("Invalid workspace")
        return {key:[str(x) for x in raw.get(key,[]) if isinstance(x,str)][:100] for key in ("favorites","recent","tool_favorites")}
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=self.path.parent,prefix=".workspace-")
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                json.dump(self.data,f,indent=2,ensure_ascii=False);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    def toggle_favorite(self,identity):
        f=self.data["favorites"]
        if identity in f:f.remove(identity)
        else:f.insert(0,identity)
        self.save()
    def mark_recent(self,identity):
        r=self.data["recent"]
        if identity in r:r.remove(identity)
        r.insert(0,identity);del r[20:]
        self.save()
    def purge(self,identity):
        for key in ("favorites","recent"):
            self.data[key]=[x for x in self.data[key] if x!=identity]
        self.save()
