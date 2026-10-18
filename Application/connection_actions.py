"""Centralized context actions for the selected connection. No network side effects.

Author: Abdelhalim Talbi.
"""

CONNECTION_ACTIONS = (
    ("Ouvrir la connexion", "connect"),
    ("Modifier", "edit"),
    ("Ajouter / retirer des favoris", "toggle_favorite"),
    ("Vérifier accès", "check_access"),
    ("Fiche de connexion", "show_connection_card"),
    ("Chronologie connexion", "show_connection_timeline"),
    ("Tester port TCP", "test_tcp_connection"),
    ("Passerelle / Rebond", "edit_route"),
    ("État PAM", "show_pam_status"),
    ("Reconnecter (session terminée)", "reconnect_selected"),
)

def actions_for_selection(connection_id):
    """Return context action descriptors only for a real connection identifier."""
    if not isinstance(connection_id, str) or not connection_id.strip():
        return ()
    return CONNECTION_ACTIONS
