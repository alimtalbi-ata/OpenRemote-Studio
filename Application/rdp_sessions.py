
"""RDP launch-file lifecycle. No credentials stored. Author: Abdelhalim Talbi."""
import os
import tempfile
import time
from pathlib import Path
from gateways import rdp_content

PREFIX='openremote-rdp-'
def write_session(directory,target,port='',username='',route=None):
    """Create unique .rdp file only after validation; avoid world-readable files on POSIX."""
    content=rdp_content(target,port,username,route)
    folder=Path(directory)
    folder.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=PREFIX,suffix='.rdp',dir=str(folder))
    try:
        if os.name=='posix':os.fchmod(fd,0o600)
        with os.fdopen(fd,'w',encoding='utf-16') as stream:
            fd=-1
            stream.write(content)
        return Path(name)
    except BaseException:
        if fd!=-1:os.close(fd)
        try:Path(name).unlink()
        except OSError:pass
        raise

def cleanup_stale(directory,max_age_seconds=86400,now=None):
    """Only remove our own old session files; never traverse subdirectories."""
    if max_age_seconds<=0:raise ValueError('Invalid retention')
    folder=Path(directory)
    if not folder.is_dir():return 0
    now=time.time() if now is None else now
    removed=0
    for item in folder.iterdir():
        if not item.name.startswith(PREFIX) or item.suffix!='.rdp' or item.is_symlink() or not item.is_file():
            continue
        try:
            if now-item.stat().st_mtime>=max_age_seconds:
                item.unlink()
                removed+=1
        except OSError:pass
    return removed
