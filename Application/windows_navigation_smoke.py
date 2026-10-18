"""Offline Qt main-window navigation smoke. Author: Abdelhalim Talbi."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = "openremote.navigation-smoke.v1"

def run_smoke(*, timeout=30, python=None, env=None):
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("timeout must be 1..120 seconds")
    child_env = dict(os.environ if env is None else env)
    child_env.setdefault("QT_QPA_PLATFORM", "offscreen")
    child_env.setdefault("QT_LOGGING_RULES", "*.debug=false")
    code = r"""
import os, tempfile, json
with tempfile.TemporaryDirectory() as tmp:
    os.environ['APPDATA'] = tmp
    from PySide6.QtWidgets import QApplication, QPushButton, QLineEdit
    import qt_app
    app = QApplication([])
    window = qt_app.Main()
    window.show()
    app.processEvents()
    menus = [a.text() for a in window.menuBar().actions()]
    buttons = [b.text() for b in window.centralWidget().findChildren(QPushButton)]
    checks = {
        'central_widget': window.centralWidget() is not None,
        'menus': all(any(name in m for m in menus) for name in ('Connexions', 'Sécurité', 'Outils')),
        'primary_actions': all(any(name in b for b in buttons) for name in ('Connexion', 'SSH', 'SFTP')),
        'home_tab': window.tabs.count() >= 1 and window.tabs.tabText(0) == 'Accueil',
        'search_field': isinstance(window.search, QLineEdit),
        'search_focus': False,
        'home_navigation': False,
    }
    window.search.setFocus()
    app.processEvents()
    checks['search_focus'] = window.search.hasFocus()
    window.tabs.setCurrentWidget(window.home)
    app.processEvents()
    checks['home_navigation'] = window.tabs.currentWidget() is window.home
    window.close()
    app.processEvents()
    print('NAV_SMOKE_JSON=' + json.dumps(checks, sort_keys=True))
"""
    try:
        result = subprocess.run([python or sys.executable, "-c", code],
            cwd=str(Path(__file__).resolve().parent), env=child_env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"schema":SCHEMA,"status":"timeout","checks":{},"network_tests_executed":False}
    except OSError:
        return {"schema":SCHEMA,"status":"launcher_error","checks":{},"network_tests_executed":False}
    checks = {}
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.startswith('NAV_SMOKE_JSON='):
                try:
                    value=json.loads(line.split('=',1)[1])
                    if isinstance(value,dict) and all(type(v) is bool for v in value.values()):
                        checks=value
                except (ValueError, TypeError):
                    pass
    passed = bool(checks) and all(checks.values())
    return {"schema":SCHEMA,"status":"passed" if passed else "failed",
        "checks":checks,"exit_code":result.returncode,"network_tests_executed":False,
        "note":"Offscreen widget structure and focus only; no screenshot, DPI, or live protocol test."}

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=30)
    args=parser.parse_args(argv)
    report=run_smoke(timeout=args.timeout)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,ensure_ascii=False)
        stream.write('\n')
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':sys.exit(main())
