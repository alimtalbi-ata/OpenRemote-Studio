"""Reusable, keyboard-accessible landing workspace. Author: Abdelhalim Talbi."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton


def create_home_header(handlers):
    """Create a compact start area; no handler is called until user clicks."""
    required = ('add', 'connect', 'check_access', 'show_session_overview', 'show_local_readiness', 'show_session_history', 'show_incident_overview', 'focus_connection_search')
    for name in required:
        if name not in handlers or not callable(handlers[name]):
            raise ValueError('Missing home action: ' + name)
    header = QWidget()
    layout = QVBoxLayout(header)
    title = QLabel('ACCUEIL  /  Infrastructure & accès distants')
    title.setObjectName('homeWorkspaceTitle')
    layout.addWidget(title)
    steps = QLabel('1. Sélectionner une connexion  →  2. Vérifier l’accès  →  3. Ouvrir la session')
    steps.setWordWrap(True)
    layout.addWidget(steps)
    # Primary connection actions already live in the persistent toolbar.
    # Avoid repeating them on the home page: this area is for orientation
    # and shortcuts to less-visible workflows only.
    guidance = QLabel('Pour commencer : recherchez un serveur dans la barre supérieure, puis utilisez Ouvrir. ' 
                      'Les favoris et les connexions récentes sont accessibles ci-dessous.')
    guidance.setObjectName('homePrimaryGuidance')
    guidance.setWordWrap(True)
    layout.addWidget(guidance)
    # Secondary shortcuts consolidate the workflow without opening extra portals.
    secondary = QHBoxLayout()
    for caption, key, tip in (
        ('Rechercher un serveur', 'focus_connection_search', 'Placer le curseur dans la recherche des connexions'),
        ('Sessions actives', 'show_session_overview', 'Voir les processus clients actifs et terminés'),
        ('Historique des sessions', 'show_session_history', 'Consulter les sessions passées'),
        ('Incidents de connexion', 'show_incident_overview', 'Analyser les échecs récents'),
    ):
        button = QPushButton(caption)
        button.setObjectName('homeShortcut_' + key)
        button.setAccessibleName(caption)
        button.setToolTip(tip)
        button.clicked.connect(handlers[key])
        secondary.addWidget(button)
    layout.addLayout(secondary)
    return header
