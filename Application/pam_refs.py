"""Non-secret PAM reference validation and capability matrix.
No authentication, network requests or secret retrieval.
Author: Abdelhalim Talbi.
"""
from dataclasses import dataclass
import re

PROVIDERS={
    "cyberark":("CyberArk", "PVWA/PSM"),
    "beyondtrust":("BeyondTrust", "Password Safe / PRA"),
    "delinea":("Delinea", "Secret Server"),
    "generic":("Generic PAM", "External vault reference"),
}
REFERENCE=re.compile(r"^(cyberark|beyondtrust|delinea|generic):([A-Za-z0-9][A-Za-z0-9_./-]{0,190})$",re.ASCII)
FORBIDDEN=("password=", "passwd=", "token=", "secret=", "apikey=", "api_key=", "://", "@")

@dataclass(frozen=True)
class PamReference:
    provider: str
    object_id: str
    display: str

def parse_reference(value):
    """Require provider:object-id; do not interpret URIs or credentials."""
    if not isinstance(value,str):raise ValueError("Référence PAM invalide")
    if not value:return None
    if len(value)>210 or any(x in value.lower() for x in FORBIDDEN):
        raise ValueError("Ne saisissez jamais un secret ou une URL dans la référence PAM")
    match=REFERENCE.fullmatch(value)
    if not match:raise ValueError("Format PAM attendu : fournisseur:identifiant")
    provider,identifier=match.groups()
    if ".." in identifier or "//" in identifier:
        raise ValueError("Identifiant PAM ambigu")
    return PamReference(provider,identifier,PROVIDERS[provider][0])

def capability_report(reference):
    parsed=parse_reference(reference)
    if parsed is None:
        return {"configured":False,"provider":None,"reference":None,
                "secret_access":False,"session_broker":False,
                "message":"Aucune référence PAM configurée"}
    return {"configured":True,"provider":parsed.display,"reference":parsed.object_id,
            "secret_access":False,"session_broker":False,
            "message":"Référence validée ; connecteur non installé, aucun accès au coffre"}
