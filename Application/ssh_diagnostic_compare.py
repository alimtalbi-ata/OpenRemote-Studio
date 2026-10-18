"""Compare redacted SSH diagnostics, without network identifiers. Author: Abdelhalim Talbi."""
import json
from ssh_diagnostic_report import summarize

_ALLOWED={'Bastion principal','Serveur cible','Diagnostic'}
def _read(report):
    if isinstance(report,str):
        if len(report)>65536:raise ValueError('Rapport trop volumineux')
        try:report=json.loads(report)
        except (ValueError,TypeError) as exc:raise ValueError('JSON invalide') from exc
    if not isinstance(report,dict) or report.get('schema')!='openremote.ssh-diagnostic.v1':raise ValueError('Schéma de rapport invalide')
    if report.get('status') not in ('authenticated','failed','cancelled'):raise ValueError('État de rapport invalide')
    steps=report.get('steps')
    if not isinstance(steps,list) or len(steps)>24:raise ValueError('Étapes invalides')
    result={}
    for row in steps:
        if not isinstance(row,dict):raise ValueError('Étape invalide')
        name=row.get('step');state=row.get('state')
        if not isinstance(name,str) or not (name in _ALLOWED or (name.startswith('Bastion ') and name[8:].isdigit() and 2<=int(name[8:])<=4)):
            raise ValueError('Identifiant de saut invalide')
        if state not in ('starting','ok','failed','cancelled'):raise ValueError('État de saut invalide')
        duration=row.get('duration_ms')
        if duration is not None and (type(duration) is not int or not 0<=duration<=3600000):raise ValueError('Durée invalide')
        result[name]={'state':state,'duration_ms':duration}
    return report['status'],result

def compare_reports(previous,current):
    old_status,old=_read(previous);new_status,new=_read(current)
    ordered=['Bastion principal','Bastion 2','Bastion 3','Bastion 4','Serveur cible','Diagnostic']
    changes=[]
    for name in ordered:
        if name not in old and name not in new:continue
        a=old.get(name);b=new.get(name)
        a_ms=a['duration_ms'] if a else None;b_ms=b['duration_ms'] if b else None
        changes.append({'step':name,'previous_state':a['state'] if a else None,'current_state':b['state'] if b else None,
                        'previous_ms':a_ms,'current_ms':b_ms,
                        'delta_ms':b_ms-a_ms if a_ms is not None and b_ms is not None else None})
    return {'schema':'openremote.ssh-comparison.v1','previous_status':old_status,'current_status':new_status,'steps':changes,
            'note':'Comparaison par position de saut, pas par identité serveur ; mêmes parcours requis pour interpréter les écarts.'}

def compare_with_result(previous,current_result):
    return compare_reports(previous,summarize(current_result))
