"""Offline infrastructure inventory and safe export. Author: Abdelhalim Talbi."""
import csv, io, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

def inventory(items):
    rows=[]
    for c in items:
        rows.append({k:str(c.get(k,'')).strip() for k in ('name','protocol','host','port','user','group','tags')})
    return sorted(rows,key=lambda r:(r['group'].casefold(),r['name'].casefold()))

def summary(items):
    rows=inventory(items)
    return {'total':len(rows),'protocols':dict(sorted(Counter(x['protocol'] for x in rows).items())),
            'groups':dict(sorted(Counter(x['group'] or 'Sans groupe' for x in rows).items()))}

def export_csv(items):
    output=io.StringIO(newline='')
    fields=['name','protocol','host','port','user','group','tags']
    writer=csv.DictWriter(output,fieldnames=fields,lineterminator='\n')
    writer.writeheader()
    for row in inventory(items):
        writer.writerow({k:("'"+v if v and v[0] in '=+-@\t\r' else v) for k,v in row.items()})
    return output.getvalue()

def export_json(items):
    return json.dumps({'schema':'openremote-inventory-v1','exported_at':datetime.now(timezone.utc).isoformat(),
                       'summary':summary(items),'connections':inventory(items)},ensure_ascii=False,indent=2)
