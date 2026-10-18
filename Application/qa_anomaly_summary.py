"""Sanitized QA anomaly inventory for OpenRemote Studio. Author: Abdelhalim Talbi."""
import argparse,json,sys
from pathlib import Path
CHECKS=("main","navigation","accessibility","layout","widgets","dialogs")
STATUSES={"passed","failed","timeout","launcher_error","blocked","not_executed"}
def summarize(report):
    if not isinstance(report,dict) or report.get("schema")!="openremote.windows-qa-campaign.v1":
        raise ValueError("unsupported campaign report")
    source=report.get("reports")
    if not isinstance(source,dict):
        # Older consolidator names this field differently; inspect before accepting.
        source=report.get("checks")
    if not isinstance(source,dict):raise ValueError("missing checks")
    if set(source)!=set(CHECKS):raise ValueError("unexpected check inventory")
    anomalies=[];counts={s:0 for s in sorted(STATUSES)}
    for name in CHECKS:
        item=source[name]
        if not isinstance(item,dict) or item.get("status") not in STATUSES:raise ValueError("invalid check status")
        status=item["status"];counts[status]+=1
        if status!="passed":anomalies.append({"check":name,"status":status,"next_action":("Install PySide6 and rerun on Windows" if status=="blocked" else "Run the Windows UI test and inspect its local report" if status=="not_executed" else "Investigate the local check and rerun")})
    return {"schema":"openremote.qa-anomalies.v1","overall":"passed" if not anomalies else "incomplete" if all(a["status"] in {"blocked","not_executed"} for a in anomalies) else "failed","counts":counts,"anomalies":anomalies,"windows_visual_qualified":False,"live_network_qualified":False}
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("input",type=Path);p.add_argument("--output",type=Path,required=True);a=p.parse_args(argv)
    result=summarize(json.loads(a.input.read_text(encoding="utf8")))
    with a.output.open("x",encoding="utf8") as f:json.dump(result,f,indent=2);f.write("\n")
    return 0 if result["overall"]=="passed" else 1
if __name__=="__main__":sys.exit(main())
