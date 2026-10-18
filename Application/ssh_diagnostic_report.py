"""Anonymized SSH diagnostic export. No hosts, accounts, route or exception text.
Author: Abdelhalim Talbi.
"""
import json
from ssh_diagnostic_view import stage_rows

def summarize(result):
    if not isinstance(result,dict) or result.get('status') not in ('authenticated','failed','cancelled'):
        raise ValueError('Résultat SSH invalide')
    rows=stage_rows(result.get('events',[]),result['status'])
    completed=[r for r in rows if r['state'] in ('ok','failed')]
    durations=[r['duration_ms'] for r in completed if r['duration_ms'] is not None]
    failure=next((r['step'] for r in completed if r['state']=='failed'),None)
    return {'schema':'openremote.ssh-diagnostic.v1','status':result['status'],
            'steps':[{'step':r['step'],'state':r['state'],**({'duration_ms':r['duration_ms']} if r.get('duration_ms') is not None else {})} for r in rows],
            'completed_steps':len(completed),'measured_steps':len(durations),
            'total_measured_ms':sum(durations),'failed_step':failure,
            'note':'Durées par étape observées localement ; somme partielle, pas une durée totale de session. Aucun hôte, compte, secret ni exception.'}

def export_json(result):
    return json.dumps(summarize(result),ensure_ascii=False,indent=2,sort_keys=True)+'\n'
