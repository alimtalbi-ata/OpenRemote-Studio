"""Run the existing Qt checks as one offline campaign. Author: Abdelhalim Talbi."""
import argparse,importlib.util,json,subprocess,sys
from pathlib import Path
from qualification_consolidator import consolidate

CHECKS={
 "main":"windows_main_smoke.py",
 "navigation":"windows_navigation_smoke.py",
 "accessibility":"windows_accessibility_smoke.py",
 "layout":"windows_layout_audit.py",
 "widgets":"windows_widget_audit.py",
 "dialogs":"windows_dialog_audit.py",
}

def campaign(*,timeout=40,runner=None,python=None):
 if type(timeout) is not int or not 1<=timeout<=120:raise ValueError("timeout must be 1..120")
 runner=runner or subprocess.run
 reports={};base=Path(__file__).resolve().parent
 if importlib.util.find_spec("PySide6") is None:
  reports={name:{"status":"blocked","schema":"openremote.qa.blocked.v1","reason":"PySide6 unavailable"} for name in CHECKS}
 else:
  for name,script in CHECKS.items():
   try:
    # Execute each existing check in its own process, without writing intermediate reports.
    # Child emits the structured report only to a temporary location managed by this campaign.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="openremote-qa-") as td:
     report_path=Path(td)/"result.json"
     proc=runner([python or sys.executable,str(base/script),"--output",str(report_path),"--timeout",str(timeout)],cwd=str(base),capture_output=True,text=True,timeout=timeout+5,check=False)
     if report_path.is_file():
      try:
       data=json.loads(report_path.read_text(encoding="utf8"))
       if not isinstance(data,dict) or data.get("status") not in {"passed","failed","timeout","launcher_error","blocked","not_executed"}:raise ValueError("invalid status")
       reports[name]=data
      except (ValueError,UnicodeError):reports[name]={"status":"failed","reason":"invalid report"}
     else:reports[name]={"status":"failed","reason":"missing report","exit_code":proc.returncode}
   except subprocess.TimeoutExpired:reports[name]={"status":"timeout"}
   except OSError:reports[name]={"status":"launcher_error"}
 result=consolidate(reports)
 result["schema"]="openremote.windows-qa-campaign.v1"
 result["environment"]={"platform":sys.platform,"pyside6_present":importlib.util.find_spec("PySide6") is not None}
 result["live_network_tests_executed"]=False
 result["windows_dpi_validated"]=False
 return result

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);p.add_argument("--timeout",type=int,default=40)
 args=p.parse_args(argv)
 result=campaign(timeout=args.timeout)
 with args.output.open("x",encoding="utf8") as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
 return 0 if result["overall"]=="passed" else 1
if __name__=="__main__":sys.exit(main())
