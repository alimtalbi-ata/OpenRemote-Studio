"""Conservative correlation of local process evidence with an offline access path.
Never assigns a remote failure to a specific hop without hop-level proof.
Author: Abdelhalim Talbi.
"""
from connection_path_diagnostics import topology, CHECKS


def correlate(protocol, route=None, *, attempts=0, failures=0, unknown=0, local_ready=None):
    for value in (attempts, failures, unknown):
        if type(value) is not int or value < 0:
            raise ValueError('invalid local counters')
    if failures + unknown > attempts:
        raise ValueError('inconsistent local counters')
    if local_ready not in (None, True, False):
        raise ValueError('invalid readiness')
    result=topology(protocol,route)
    nodes=[dict(node) for node in result['nodes']]
    # Local readiness is the only evidence that can be assigned to a hop.
    if local_ready is False:
        nodes[0]['status']='prerequis_locaux_a_corriger'
    for node in nodes[1:]:
        node['status']='non_verifie'
    if failures:
        assessment='echec_processus_local_observe'
        advice='Consulter le code de sortie du client ; aucun saut distant ne peut être incriminé.'
    elif unknown:
        assessment='fin_session_non_observee'
        advice='Vérifier la fermeture du client ; la session distante ne peut être déclarée réussie.'
    elif attempts:
        assessment='aucun_echec_processus_local_observe'
        advice='Le résultat du processus local ne prouve pas la disponibilité de la cible.'
    else:
        assessment='aucune_tentative_locale'
        advice='Effectuer les précontrôles locaux avant toute connexion.'
    return {'schema':'openremote.path-evidence.v1','protocol':protocol,
            'network_tested':False,'hop_failure_confirmed':False,
            'local':{'attempts':attempts,'failures':failures,'unknown':unknown,
                     'ready':local_ready,'assessment':assessment},
            'nodes':nodes,'advice':advice}


def format_evidence(report):
    if report.get('schema')!='openremote.path-evidence.v1' or report.get('network_tested') is not False or report.get('hop_failure_confirmed') is not False:
        raise ValueError('invalid report')
    nodes=report.get('nodes')
    if not isinstance(nodes,list) or not nodes or any(not isinstance(n,dict) or n.get('kind') not in CHECKS or n.get('status') not in ('non_verifie','prerequis_locaux_a_corriger') for n in nodes):
        raise ValueError('invalid nodes')
    local=report.get('local',{})
    if local.get('assessment') not in ('echec_processus_local_observe','fin_session_non_observee','aucun_echec_processus_local_observe','aucune_tentative_locale'):
        raise ValueError('invalid assessment')
    return ('Corrélation locale du parcours — hors ligne\n'
            'Aucune panne de bastion ou de cible confirmée.\n\n'
            + '\n'.join(f"{i}. {n['kind']} : {n['status']} — {CHECKS[n['kind']]}" for i,n in enumerate(nodes,1))
            + '\n\nConstat : '+local['assessment']+'\n'+{
              'echec_processus_local_observe':'Un échec du client local a été observé, sans localisation du saut défaillant.',
              'fin_session_non_observee':'La fin du client n’a pas été observée.',
              'aucun_echec_processus_local_observe':'Aucun échec du client local observé, sans preuve de succès distant.',
              'aucune_tentative_locale':'Aucune tentative locale enregistrée.'}[local['assessment']])
