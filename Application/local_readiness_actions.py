"""Offline, non-invasive client repair guidance. Author: Abdelhalim Talbi."""

HELP = {
    "SSH": "Windows : Paramètres > Fonctionnalités facultatives > Client OpenSSH. Vérifier ssh.exe avec `where ssh`.",
    "SFTP": "Installer ou activer le Client OpenSSH Windows, puis vérifier sftp.exe avec `where sftp`.",
    "RDP": "Windows : vérifier la présence de mstsc.exe. Les éditions et stratégies Windows peuvent limiter son utilisation.",
    "VNC": "Installer un client VNC compatible depuis son fournisseur, vérifier sa licence et sa présence dans le PATH.",
}

def repair_guidance(report):
    """Return local-only repair hints; never execute installers or inspect credentials."""
    if not isinstance(report, dict) or report.get("scope") != "local_only" or report.get("network_tested") is not False:
        raise ValueError("Invalid diagnostic scope")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) > 32:
        raise ValueError("Invalid inventory")
    hints = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("protocol") not in HELP:
            raise ValueError("Invalid protocol")
        protocol = row["protocol"]
        if protocol not in seen and row.get("ready") is not True:
            hints.append(f"{protocol} : {HELP[protocol]}")
            seen.add(protocol)
    return "\n".join(hints) if hints else "Aucune correction locale suggérée. Les connexions distantes ne sont pas testées."
