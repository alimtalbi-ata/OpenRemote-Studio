"""Credential-free protocol troubleshooting guide; never performs network I/O.
Author: Abdelhalim Talbi.
"""

GUIDES = {
    "SSH": ("Contrôler la résolution DNS et le port TCP 22 (ou port configuré).", "Vérifier l’empreinte de la clé hôte et les méthodes d’authentification autorisées.", "Pour un rebond, vérifier chaque bastion et ses autorisations."),
    "SFTP": ("Vérifier le transport SSH et les droits sur le répertoire distant.", "Contrôler l’espace disponible et les quotas avant transfert.", "Ne pas relancer un transfert partiel sans vérification d’intégrité."),
    "RDP": ("Vérifier le port TCP 3389 ou le port défini, et la politique du pare-feu.", "Contrôler l’autorisation RDP et les exigences NLA/TLS.", "En présence d’une passerelle, vérifier RD Gateway et les politiques CAP/RAP."),
    "VNC": ("Vérifier le port VNC et la compatibilité du client local.", "Privilégier un tunnel sécurisé plutôt qu’un VNC exposé directement.", "Vérifier les méthodes d’authentification et le chiffrement disponibles."),
    "WEB": ("Vérifier DNS, TLS et la chaîne de certificats du site.", "Contrôler le proxy et les politiques d’accès.", "Ne pas enregistrer les jetons présents dans les URL."),
}

def guidance(protocol, *, local_ready=None, failures=0, unknown=0, pam=False):
    """Return deterministic advice without hostnames, usernames or secrets."""
    if protocol not in GUIDES: raise ValueError("unsupported protocol")
    if type(failures) is not int or failures < 0 or type(unknown) is not int or unknown < 0:
        raise ValueError("invalid counts")
    steps=list(GUIDES[protocol])
    if local_ready is False:
        steps.insert(0, "Corriger d’abord les prérequis locaux dans Vérifier accès.")
    if failures:
        steps.append("Consulter les codes de sortie locaux et l’historique des diagnostics.")
    if unknown:
        steps.append("La fin de session n’est pas observée : ne pas conclure à une connexion réussie.")
    if pam:
        steps.append("Contrôler les droits du coffre PAM, l’expiration du bail et le chemin de rebond ; ne jamais exposer le secret.")
    return {"protocol":protocol,"network_tested":False,"remote_authenticated":False,"steps":steps}

def format_guidance(result):
    if result.get("protocol") not in GUIDES or result.get("network_tested") is not False:
        raise ValueError("invalid guidance")
    return "Diagnostic guidé — "+result["protocol"]+"\nAucun test réseau effectué.\n\n"+"\n".join(f"{i}. {step}" for i,step in enumerate(result["steps"],1))
