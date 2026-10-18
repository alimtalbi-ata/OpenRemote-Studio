"""Merge local process and probe metadata without inventing remote success.
Author: Abdelhalim Talbi.
"""
from datetime import datetime, timezone

def _stamp(value):
    if not isinstance(value,str):return ''
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        if d.tzinfo is None:return ''
        return d.astimezone(timezone.utc).isoformat()
    except ValueError:return ''

def timeline(sessions,probes,connection_id,limit=100,kind='all'):
    if not isinstance(connection_id,str) or not connection_id:raise ValueError('connection_id requis')
    if type(limit) is not int or not 1<=limit<=500:raise ValueError('limite invalide')
    if kind not in ('all','session','probe','error'):raise ValueError('filtre invalide')
    result=[]
    for s in sessions:
        if s.get('connection_id')!=connection_id:continue
        start=_stamp(s.get('started_at'))
        if start:result.append({'at':start,'kind':'session','state':'started','detail':'Client '+str(s.get('protocol',''))+' lancé'})
        end=_stamp(s.get('finished_at'))
        if end:
            code=s.get('exit_code')
            state='unknown' if type(code) is not int else ('zero_exit' if code==0 else 'error')
            result.append({'at':end,'kind':'session','state':state,'detail':'Code de sortie '+str(code) if type(code) is int else 'Sortie inconnue'})
    for p in probes:
        if len(p)!=4 or p[0]!=connection_id:continue
        at=_stamp(p[3])
        if at and p[1] in ('tcp_local','ssh_jump') and p[2] in ('ok','failed','unknown'):
            result.append({'at':at,'kind':'probe','state':p[2], 'detail':p[1]})
    if kind=='error':result=[r for r in result if r['state'] in ('error','failed')]
    elif kind!='all':result=[r for r in result if r['kind']==kind]
    return sorted(result,key=lambda r:r['at'],reverse=True)[:limit]

def export_timeline(rows):
    """CSV for local audit, no host/user/command/secret fields."""
    import csv,io
    out=io.StringIO();writer=csv.writer(out,lineterminator='\n')
    writer.writerow(('utc','category','state','detail'))
    for row in rows:writer.writerow((row['at'],row['kind'],row['state'],row['detail']))
    return out.getvalue()
