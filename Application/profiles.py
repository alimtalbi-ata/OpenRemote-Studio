"""Professional toolbox views: filtering only, no permissions implied.
Author: Abdelhalim Talbi.
"""
PROFILES = {
    "Tous": None,
    "Système": frozenset(("Réseau", "Accès", "Sécurité", "Espace de travail")),
    "Réseau": frozenset(("Réseau", "Accès", "Sécurité")),
    "Stockage / SAN": frozenset(("Réseau", "Accès", "Sécurité")),
    "DevOps": frozenset(("Accès", "Réseau", "Espace de travail", "Sécurité")),
    "AIOps": frozenset(("Réseau", "Accès", "Espace de travail", "Sécurité")),
}
def visible_tools(tools, profile, query=""):
    if profile not in PROFILES:
        raise ValueError("Profil inconnu")
    categories = PROFILES[profile]
    q = query.strip().casefold()
    return [tool for tool in tools if (categories is None or tool[0] in categories)
            and (not q or q in " ".join(tool).casefold())]
