"""Local process evidence summary for connection card. No remote uptime inference.
Author: Abdelhalim Talbi.
"""

def summarize_connection(rows, identity):
    matches=[r for r in rows if r.get('connection_id')==identity]
    attempts=sum(r['attempts'] for r in matches)
    observed=sum(r['observed'] for r in matches)
    failures=sum(r['failed'] for r in matches)
    unknown=sum(r['unobserved'] for r in matches)
    if not attempts:
        status='Aucune tentative locale enregistrée'
        advice='Vérifier les paramètres de connexion avant le premier lancement.'
    elif failures:
        status='Échecs de processus locaux observés'
        advice='Consulter les codes de sortie et les diagnostics de chemin réseau.'
    elif unknown:
        status='Terminaisons non observées'
        advice='Contrôler le client externe ; ne pas conclure à une réussite.'
    else:
        status='Aucun échec local observé'
        advice='Un code zéro ne garantit pas une session distante fonctionnelle.'
    return {'attempts':attempts,'observed':observed,'failures':failures,'unknown':unknown,
            'coverage':round(observed*100/attempts,1) if attempts else None,
            'status':status,'advice':advice}
