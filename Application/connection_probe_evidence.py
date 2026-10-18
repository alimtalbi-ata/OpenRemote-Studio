"""Conservative mapping of recorded local probes to access-path evidence.
No remote hop attribution from a workstation-side TCP check.
Author: Abdelhalim Talbi.
"""
from connection_path_diagnostics import topology

KINDS = {'tcp_local', 'ssh_jump'}
OUTCOMES = {'ok', 'failed', 'unknown'}

def correlate_probes(protocol, route=None, records=()):
    path = topology(protocol, route)
    if not isinstance(records, (list, tuple)) or len(records) > 500:
        raise ValueError('invalid probe records')
    events=[]
    for record in records:
        if not isinstance(record,(list,tuple)) or len(record)!=2:
            raise ValueError('invalid probe record')
        kind,outcome=record
        if kind not in KINDS or outcome not in OUTCOMES:
            raise ValueError('invalid probe result')
        if kind=='tcp_local':
            meaning={'ok':'Port TCP joignable depuis le poste, sans preuve de succès applicatif.',
                     'failed':'Connexion TCP depuis le poste en échec ; saut distant indéterminé.',
                     'unknown':'Résultat TCP indéterminé.'}[outcome]
        else:
            meaning={'ok':'Sortie du contrôle SSH observée ; chaîne distante non confirmée.',
                     'failed':'Échec du contrôle SSH ; saut en cause non identifié.',
                     'unknown':'Résultat SSH indéterminé ; aucun saut confirmé.'}[outcome]
        events.append({'kind':kind,'outcome':outcome,'scope':'poste_local',
                       'hop_index':None,'interpretation':meaning})
    return {'schema':'openremote.probe-evidence.v1','protocol':protocol,
            'network_tested_by_this_report':False,'hop_failure_confirmed':False,
            'nodes':path['nodes'],'events':events,'status':'observations_locales' if events else 'aucune_preuve'}

def format_probe_evidence(report):
    if report.get('schema')!='openremote.probe-evidence.v1' or report.get('hop_failure_confirmed') is not False or report.get('network_tested_by_this_report') is not False:
        raise ValueError('invalid report')
    events=report.get('events')
    if not isinstance(events,list) or any(not isinstance(e,dict) or e.get('kind') not in KINDS or e.get('outcome') not in OUTCOMES or e.get('scope')!='poste_local' or e.get('hop_index') is not None for e in events):
        raise ValueError('invalid events')
    descriptions={
      ('tcp_local','ok'):'TCP accessible depuis le poste (service non authentifié)',
      ('tcp_local','failed'):'Échec TCP depuis le poste (cause distante inconnue)',
      ('tcp_local','unknown'):'TCP : résultat indéterminé',
      ('ssh_jump','ok'):'Contrôle SSH terminé sans confirmation de la cible',
      ('ssh_jump','failed'):'Contrôle SSH en échec (saut inconnu)',
      ('ssh_jump','unknown'):'Contrôle SSH : résultat indéterminé',
    }
    return ('Chronologie des observations locales\nAucun saut distant déclaré en panne.\n'
            + ('\n'.join(f"{i}. {descriptions[(e['kind'],e['outcome'])]}" for i,e in enumerate(events,1)) if events else 'Aucune observation disponible.'))
