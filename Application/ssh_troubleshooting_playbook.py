"""Evidence-first, non-invasive SSH troubleshooting playbooks. Author: Abdelhalim Talbi."""
from ssh_failure_guidance import classify

CHECKS = {
 'failed_stage': (
  ('Réseau', 'Vérifier le chemin TCP/22 et les règles de filtrage depuis le saut précédent.'),
  ('Confiance', 'Vérifier known_hosts et la correspondance de la clé hôte sans désactiver StrictHostKeyChecking.'),
  ('Authentification', 'Contrôler les droits du compte, la clé autorisée et les journaux SSH côté serveur.'),
 ),
 'unlocated_failure': (
  ('Réseau', 'Vérifier DNS, routage, VPN et accessibilité TCP sans modifier les pare-feu.'),
  ('Service', 'Contrôler la disponibilité de sshd et les journaux du serveur autorisé.'),
 ),
 'cancelled': (('Exécution', 'Vérifier la raison de l’annulation avant toute nouvelle tentative.'),),
 'slow_stage': (
  ('Mesure', 'Comparer médiane et P95 sur plusieurs mesures du même parcours.'),
  ('Infrastructure', 'Vérifier charge, DNS et délais de négociation avec les équipes habilitées.'),
 ),
 'authenticated': (('Contrôle', 'Aucune intervention requise sur la base de ce seul diagnostic.'),),
}

def build_playbook(result, slow_threshold_ms=2000):
    """Return a bounded, redacted structured report. Never include raw error text."""
    finding=classify(result,slow_threshold_ms)
    code=finding['code']
    evidence=[]
    if code=='failed_stage': evidence.append('Échec observé à l’étape : '+finding['stage'])
    elif code=='unlocated_failure': evidence.append('Échec signalé sans étape défaillante identifiable')
    elif code=='cancelled': evidence.append('Exécution annulée')
    elif code=='slow_stage': evidence.append('Au moins une durée dépasse le seuil configuré')
    else: evidence.append('Authentification réussie pendant le test')
    return {'schema':'openremote.ssh.playbook.v1','classification':code,
            'title':finding['title'],'evidence':evidence,
            'hypotheses':([] if code in ('cancelled','authenticated') else
                          ['La cause technique exacte n’est pas démontrée par les événements anonymisés.']),
            'checks':[{'category':category,'instruction':instruction} for category,instruction in CHECKS[code]],
            'automatic_changes':False}

def format_playbook(report):
    if not isinstance(report,dict) or report.get('schema')!='openremote.ssh.playbook.v1':
        raise ValueError('Rapport de dépannage invalide')
    lines=['Dépannage guidé — '+report['title'],'Constats observés :']
    lines.extend(' • '+item for item in report['evidence'])
    if report['hypotheses']:
        lines.append('Hypothèses non confirmées :')
        lines.extend(' • '+item for item in report['hypotheses'])
    lines.append('Vérifications proposées (lecture seule) :')
    lines.extend(' • '+item['category']+' : '+item['instruction'] for item in report['checks'])
    return '\n'.join(lines)
