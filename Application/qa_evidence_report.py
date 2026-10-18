"""Offline, redacted HTML summary of Windows QA campaign results. Abdelhalim Talbi."""
import argparse, html, json, sys
from pathlib import Path

CHECK_NAMES = ("main", "navigation", "accessibility", "layout", "widgets", "dialogs")
STATES = {"passed", "failed", "timeout", "launcher_error", "blocked", "not_executed"}

def render(report):
    """Render only allowlisted fields; never interpolate arbitrary error text or paths."""
    if not isinstance(report, dict) or report.get("schema") != "openremote.windows-qa-campaign.v1":
        raise ValueError("invalid campaign schema")
    results = report.get("reports")
    if not isinstance(results, dict) or set(results) != set(CHECK_NAMES):
        raise ValueError("missing or unexpected checks")
    rows=[]
    for name in CHECK_NAMES:
        item=results[name]
        if not isinstance(item,dict) or item.get("status") not in STATES:
            raise ValueError("invalid check status")
        rows.append("<tr><th scope=\"row\">"+html.escape(name)+"</th><td>"+html.escape(item["status"])+"</td></tr>")
    overall=report.get("overall")
    if overall not in {"passed", "failed", "incomplete"}:
        raise ValueError("invalid overall status")
    # A successful offline campaign must never be represented as Windows acceptance.
    return ("<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>OpenRemote Studio — Qualification V13.3</title>"
            "<style>body{font:16px system-ui,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;line-height:1.5}"
            "table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:.65rem;text-align:left}"
            "thead{background:#eee} .warning{border-left:4px solid #b36b00;padding:1rem;background:#fff6e5}</style>"
            "</head><body><h1>OpenRemote Studio — Qualification V13.3</h1>"
            "<p>Auteur : Abdelhalim Talbi</p><p>Résultat hors ligne : <strong>"+html.escape(overall)+"</strong></p>"
            "<p class=\"warning\">La réussite des contrôles hors ligne ne valide pas Windows, les facteurs DPI, "
            "les captures d’écran réelles ni les connexions SSH/RDP/VNC/SFTP/PAM.</p>"
            "<table><thead><tr><th>Contrôle</th><th>État</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table>"
            "<p>Preuves visuelles Windows : non fournies. Qualification réseau réelle : non exécutée.</p>"
            "</body></html>\n")

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    if args.input.resolve()==args.output.resolve():
        parser.error("input and output must differ")
    with args.input.open("r",encoding="utf-8") as stream:
        report=json.load(stream)
    content=render(report)
    with args.output.open("x",encoding="utf-8") as stream:
        stream.write(content)
    return 0

if __name__=="__main__": sys.exit(main())
