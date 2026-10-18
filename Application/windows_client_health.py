"""Local Windows client inventory. No network access. Author: Abdelhalim Talbi."""
import os
import shutil

CLIENTS = (("SSH", "ssh"), ("SFTP", "sftp"), ("RDP", "mstsc"), ("VNC", "vncviewer"))

def inspect_clients(which=None, platform=None):
    """Return local client availability; never probe hosts or read credentials."""
    resolver = shutil.which if which is None else which
    system = os.name if platform is None else platform
    if system not in ("nt", "posix"):
        raise ValueError("Unsupported platform")
    rows = []
    for protocol, command in CLIENTS:
        path = resolver(command)
        installed = isinstance(path, str) and bool(path.strip())
        supported = protocol != "RDP" or system == "nt"
        rows.append({"protocol": protocol, "client": command,
                     "installed": installed, "supported": supported,
                     "ready": installed and supported,
                     "status": "Prêt (client trouvé)" if installed and supported else
                               "Windows requis" if not supported else "Client absent"})
    return {"scope": "local_only", "network_tested": False,
            "ready_count": sum(row["ready"] for row in rows), "rows": rows}
