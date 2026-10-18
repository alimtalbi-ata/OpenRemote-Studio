"""Ordered, credential-free inspector actions. Author: Abdelhalim Talbi."""

def inspector_action_groups():
    """Return UI metadata only; no network activity or command execution."""
    return (
        ('Session', (
            ('Ouvrir la connexion', 'connect', 'Démarrer une session avec le client configuré'),
            ('Vérifier l’accès', 'check_access', 'Effectuer les contrôles d’accès sur demande'),
        )),
        ('Informations', (
            ('Fiche détaillée', 'show_connection_card', 'Afficher les propriétés de la connexion'),
            ('Chronologie', 'show_connection_timeline', 'Afficher les événements de la connexion'),
        )),
    )
