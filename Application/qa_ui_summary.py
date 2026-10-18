"""Privacy-preserving Qt QA status presentation. Author: Abdelhalim Talbi."""
import json
from pathlib import Path
from qa_anomaly_summary import summarize, CHECKS

LABELS={"main":"Fenêtre principale","navigation":"Navigation","accessibility":"Accessibilité","layout":"Disposition","widgets":"Widgets","dialogs":"Dialogues"}
STATUS={"passed":"Réussi","failed":"Échec","blocked":"Bloqué","timeout":"Délai dépassé","launcher_error":"Erreur de lancement","not_executed":"Non exécuté"}

def format_campaign(report):
    """Accept only strict campaign schema; never interpolate raw user data."""
    data=summarize(report)
    entries=report.get("reports",report.get("checks"))
    lines=["Qualification de l'interface · OpenRemote Studio", "", "État : "+({"passed":"Contrôles disponibles réussis","failed":"Anomalies détectées","incomplete":"Qualification incomplète"}[data["overall"]]), ""]
    for name in CHECKS:
        lines.append(LABELS[name]+" : "+STATUS[entries[name]["status"]])
    lines.extend(["", "Qualification graphique Windows : NON VALIDÉE", "Connexions réseau réelles : NON VALIDÉES", "", "Les résultats ne contiennent ni identifiants, ni hôtes, ni traces brutes."])
    return "\n".join(lines)

def load_summary(path):
    path=Path(path)
    if not path.is_file():
        return "Aucun rapport local trouvé. Exécuter la campagne Windows depuis le menu Outils ou le lanceur dédié."
    if path.stat().st_size>1024*1024:raise ValueError("report too large")
    return format_campaign(json.loads(path.read_text(encoding="utf-8")))
