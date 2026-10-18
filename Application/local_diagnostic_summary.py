"""Pure, offline presentation model for local client readiness. Author: Abdelhalim Talbi."""

def summarize_local_clients(report):
    if not isinstance(report, dict) or report.get("scope") != "local_only" or report.get("network_tested") is not False:
        raise ValueError("invalid local diagnostic scope")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) > 32:
        raise ValueError("invalid client inventory")
    ready = 0
    missing = []
    unsupported = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("protocol"), str):
            raise ValueError("invalid client entry")
        protocol = row["protocol"]
        if protocol not in ("SSH", "SFTP", "RDP", "VNC"):
            raise ValueError("unknown protocol")
        if row.get("ready") is True:
            ready += 1
        elif row.get("supported") is False:
            unsupported.append(protocol)
        else:
            missing.append(protocol)
    headline = f"Clients locaux disponibles : {ready}/{len(rows)}"
    if not rows:
        advice = "Aucun client à inventorier."
    elif missing:
        advice = "Client(s) absent(s) : " + ", ".join(missing) + ". Vérifier l’installation et le PATH Windows."
    elif unsupported:
        advice = "Non pris en charge sur ce système : " + ", ".join(unsupported) + "."
    else:
        advice = "Clients locaux détectés. La connectivité distante n’a pas été vérifiée."
    return headline, advice
