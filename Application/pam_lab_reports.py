"""Tamper-evident local simulation audit exports, not a cryptographic signature.
Author: Abdelhalim Talbi.
"""
import hashlib,json,os,tempfile
from pathlib import Path

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')

def make_report(events):
    previous='0'*64
    chain=[]
    for number,event in enumerate(events,1):
        if not isinstance(event,dict):raise ValueError('Événement invalide')
        record={'index':number,'previous_hash':previous,'event':dict(event)}
        previous=hashlib.sha256(canonical(record)).hexdigest()
        chain.append({**record,'hash':previous})
    return {'format':'openremote-pam-lab-audit-v1','simulated_only':True,
            'events':chain,'final_hash':previous}

def verify_report(report):
    if not isinstance(report,dict) or report.get('format')!='openremote-pam-lab-audit-v1' or report.get('simulated_only') is not True:return False
    try:
        previous='0'*64
        if not isinstance(report.get('events'),list) or len(report['events'])>100000:return False
        if set(report)!={'format','simulated_only','events','final_hash'}:return False
        for index,item in enumerate(report['events'],1):
            if not isinstance(item,dict) or set(item)!={'index','previous_hash','event','hash'}:return False
            if not isinstance(item['event'],dict):return False
            if item['index']!=index or item['previous_hash']!=previous:return False
            record={k:item[k] for k in ('index','previous_hash','event')}
            digest=hashlib.sha256(canonical(record)).hexdigest()
            if item['hash']!=digest:return False
            previous=digest
        return report['final_hash']==previous
    except (KeyError,TypeError,ValueError):return False

def export_report(path,events):
    report=make_report(events)
    destination=Path(path)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.pam-lab-',suffix='.tmp',dir=destination.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as file:
            json.dump(report,file,ensure_ascii=False,indent=2)
            file.flush();os.fsync(file.fileno())
        if os.name!='nt':os.chmod(tmp,0o600)
        os.replace(tmp,destination)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return report


def load_and_verify_report(path, max_bytes=10_000_000):
    """Bounded read of untrusted JSON; no execution, network or secrets."""
    destination=Path(path)
    if destination.stat().st_size>max_bytes:raise ValueError('Rapport trop volumineux')
    with destination.open('rb') as file:
        content=file.read(max_bytes+1)
    if len(content)>max_bytes:raise ValueError('Rapport trop volumineux')
    try:report=json.loads(content.decode('utf-8'))
    except (UnicodeError,json.JSONDecodeError) as exc:raise ValueError('Rapport JSON illisible') from exc
    return {'valid':verify_report(report),'event_count':len(report.get('events',[])) if isinstance(report,dict) and isinstance(report.get('events'),list) else 0,
            'final_hash':report.get('final_hash','') if isinstance(report,dict) else ''}
