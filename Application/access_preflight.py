
"""Connection preflight without networking or credentials. Author: Abdelhalim Talbi."""
import os
import shutil
from connection_policy import connection_route

CLIENTS={"SSH":"ssh","SFTP":"sftp","RDP":"mstsc","VNC":"vncviewer"}
def inspect_access(connection,route=None,which=None,platform=None):
    which=which or shutil.which
    platform=os.name if platform is None else platform
    protocol=connection["protocol"]
    issues=[];warnings=[]
    try:
        r=connection_route(protocol,route)
    except ValueError as exc:
        return {"ready":False,"client":None,"mode":None,"issues":[str(exc)],"warnings":[]}
    mode=r["mode"] or "direct"
    client=CLIENTS.get(protocol)
    if protocol=="RDP" and platform!="nt":
        issues.append("mstsc.exe nécessite Windows")
    if client and not which(client):
        issues.append("Client externe introuvable : "+client)
    if protocol=="SFTP" and mode=="ssh_jump":
        warnings.append("Rebond disponible via le client SFTP externe uniquement")
    if r.get("vault_ref"):
        issues.append("Accès PAM demandé mais aucun connecteur authentifié disponible : session bloquée")
    if mode=="rds_collection":
        warnings.append("Collection RDS à valider avec le Connection Broker")
    return {"ready":not issues,"client":client,"mode":mode,
            "issues":issues,"warnings":warnings}
