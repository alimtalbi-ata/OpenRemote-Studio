"""Isolated full Main Qt initialization smoke test. Author: Abdelhalim Talbi."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = "openremote.main-smoke.v1"

def run_smoke(*, timeout=25, python=None, env=None):
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("timeout must be 1..120 seconds")
    child_env = dict(os.environ if env is None else env)
    child_env.setdefault("QT_QPA_PLATFORM", "offscreen")
    child_env.setdefault("QT_LOGGING_RULES", "*.debug=false")
    # All application state is redirected to an isolated temporary directory.
    code = ("import os,tempfile; "
            "from pathlib import Path; "
            "from PySide6.QtWidgets import QApplication; "
            "with_temp = tempfile.TemporaryDirectory(); "
            "os.environ['APPDATA']=with_temp.name; "
            "import qt_app; "
            "app=QApplication([]); "
            "window=qt_app.Main(); window.show(); app.processEvents(); "
            "assert window.centralWidget() is not None; "
            "window.close(); app.processEvents(); "
            "print('MAIN_SMOKE_OK')")
    try:
        result = subprocess.run([python or sys.executable, "-c", code],
            cwd=str(Path(__file__).resolve().parent), env=child_env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"schema":SCHEMA,"status":"timeout","main_window_tested":False,"network_tests_executed":False}
    except OSError:
        return {"schema":SCHEMA,"status":"launcher_error","main_window_tested":False,"network_tests_executed":False}
    ok = result.returncode == 0 and "MAIN_SMOKE_OK" in result.stdout
    return {"schema":SCHEMA,"status":"passed" if ok else "failed",
            "main_window_tested":ok,"network_tests_executed":False,
            "exit_code":result.returncode,
            "note":"Qt Main initialization and close only; no protocol sessions or Windows DPI verified."}

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--timeout",type=int,default=25)
    args=parser.parse_args(argv)
    report=run_smoke(timeout=args.timeout)
    with args.output.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2);stream.write("\n")
    return 0 if report["status"]=="passed" else 1

if __name__=="__main__":sys.exit(main())
