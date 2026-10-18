"""Safe, evidence-limited SSH troubleshooting hints. Author: Abdelhalim Talbi."""
from ssh_diagnostic_view import compact_stage_rows

GUIDANCE = {
    'failed_stage': ('Échec sur une étape SSH', 'Contrôler la connectivité, les ACL, la clé SSH et known_hosts du saut concerné. La cause exacte ne peut pas être déduite des événements anonymisés.'),
    'unlocated_failure': ('Échec SSH non localisé', 'Contrôler le réseau, la résolution DNS, les délais et les journaux côté serveur avec les autorisations appropriées.'),
    'cancelled': ('Diagnostic annulé', 'Relancer uniquement si nécessaire, après vérification des autorisations.'),
    'slow_stage': ('Latence élevée observée', 'Comparer plusieurs mesures du même parcours avant de conclure à une dégradation.'),
    'authenticated': ('Authentification réussie', 'Aucune anomalie d’authentification détectée pendant ce diagnostic.'),
}

def classify(result, slow_threshold_ms=2000):
    """Classify sanitized stages only; never inspect exceptions, hosts or secrets."""
    if not isinstance(result,dict): raise ValueError('Résultat invalide')
    status=result.get('status')
    if status not in ('authenticated','failed','cancelled'): raise ValueError('Statut invalide')
    if type(slow_threshold_ms) is not int or not 100<=slow_threshold_ms<=60000: raise ValueError('Seuil invalide')
    rows=compact_stage_rows(result.get('events',[]),status)
    failed=next((r for r in rows if r['state']=='failed'),None)
    if status=='cancelled':code='cancelled'
    elif status=='failed':code='failed_stage' if failed else 'unlocated_failure'
    elif any(r.get('duration_ms') is not None and r['duration_ms']>=slow_threshold_ms for r in rows):code='slow_stage'
    else:code='authenticated'
    title,advice=GUIDANCE[code]
    return {'code':code,'title':title,'advice':advice,'stage':failed['step'] if code=='failed_stage' else None,'confidence':'indicatif'}
