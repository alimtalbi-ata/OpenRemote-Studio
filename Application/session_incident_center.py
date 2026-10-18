"""Read-only incident index for Sessions. Author: Abdelhalim Talbi."""
from session_diagnostics import explain_session_failure
import re

_SECRET = re.compile(r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)\b\s*[:=]\s*([^\s,;]+)")

def _safe_text(value, limit):
    text = str(value)[:4096]
    text = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", text)
    text = _SECRET.sub(lambda m: m.group(1) + "=[REDACTED]", text)
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(://[^\s/@:]+:)[^\s/@]+(@)", r"\1[REDACTED]\2", text)
    text = re.sub(r"(?i)(://[^\s/@:]+:)[^\s/@]+(@)", r"\1[REDACTED]\2", text)
    text = "".join(c if c.isprintable() else " " for c in text)
    return text[:limit]


def incident_index(rows, query='', only_errors=True):
    """Build navigable cards without trusting PID alone as session identity."""
    if not isinstance(rows,(list,tuple)):
        raise TypeError('rows must be a sequence')
    result=[]
    term=str(query).strip().casefold()
    for ordinal,row in enumerate(rows):
        if not isinstance(row,dict):
            continue
        state=row.get('status')
        failed=state=='exited' and type(row.get('exit_code')) is int and row['exit_code']!=0
        uncertain=state=='unknown' or (state=='exited' and row.get('exit_code') is None)
        if only_errors and not (failed or uncertain):
            continue
        identity=row.get('connection_id')
        if not isinstance(identity,str) or not identity.strip():
            continue
        name=str(row.get('name') or identity)
        proto=str(row.get('protocol') or '').upper()
        if term and term not in (name+' '+identity+' '+proto).casefold():
            continue
        report=explain_session_failure(row)
        # Row position is only a navigation hint; consumer must revalidate process identity.
        result.append({'connection_id':identity,'row_index':ordinal,'name':name,
            'protocol':proto,'status':state,'diagnostic':report,
            'requires_revalidation':True,'can_reconnect':False})
    return sorted(result,key=lambda x:(0 if x['diagnostic']['severity']=='error' else 1,x['name'].casefold(),x['row_index']))

def incident_counts(items):
    return {'total':len(items),'errors':sum(i['diagnostic']['severity']=='error' for i in items),
            'uncertain':sum(i['diagnostic']['severity']=='warning' for i in items)}

def format_incident_index(items):
    if not items:return 'Aucune erreur locale ou session incertaine détectée.'
    return '\n\n'.join(f"{i['name']} [{i['protocol']}] — {i['diagnostic']['summary']}\n"+
        '\n'.join('• '+action for action in i['diagnostic']['actions']) for i in items)


def incident_export(items):
    """Export a sanitized support summary; never export raw process arguments or secrets."""
    if not isinstance(items,(list,tuple)):
        raise TypeError('items must be a sequence')
    safe=[]
    for item in items:
        if not isinstance(item,dict):
            continue
        diagnostic=item.get('diagnostic') or {}
        if not isinstance(diagnostic,dict):
            diagnostic={}
        safe.append({'connection_id':_safe_text(item.get('connection_id',''),128),
                     'protocol':_safe_text(item.get('protocol',''),16),
                     'severity':_safe_text(diagnostic.get('severity','unknown'),32),
                     'summary':_safe_text(diagnostic.get('summary',''),500),
                     'requires_revalidation':True,'can_reconnect':False})
    return {'schema':'openremote.incidents.v1','incidents':safe,'count':len(safe)}
