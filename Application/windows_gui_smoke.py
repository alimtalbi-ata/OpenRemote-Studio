"""Opt-in isolated Qt startup smoke test, no remote connections. Abdelhalim Talbi."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = "openremote.qt-smoke.v1"

def run_smoke(*, timeout=15, python=None, env=None):
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 120:
        raise ValueError("timeout must be 1..120 seconds")
    python = python or sys.executable
    code = ("from PySide6.QtWidgets import QApplication, QWidget; "
            "import qt_app; "
            "app=QApplication([]); w=QWidget(); w.setWindowTitle('OpenRemote Qt smoke'); "
            "w.show(); app.processEvents(); w.close(); print('QT_SMOKE_OK')")
    child_env = dict(os.environ if env is None else env)
    child_env.setdefault("QT_LOGGING_RULES", "*.debug=false")
    try:
        result = subprocess.run([python, "-c", code], cwd=str(Path(__file__).resolve().parent),
                                env=child_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"schema": SCHEMA, "status": "timeout", "qt_initialized": False,
                "main_window_tested": False, "network_tests_executed": False}
    except OSError:
        return {"schema": SCHEMA, "status": "launcher_error", "qt_initialized": False,
                "main_window_tested": False, "network_tests_executed": False}
    ok = result.returncode == 0 and "QT_SMOKE_OK" in result.stdout
    return {"schema": SCHEMA, "status": "passed" if ok else "failed",
            "qt_initialized": ok, "main_window_tested": False,
            "network_tests_executed": False, "exit_code": result.returncode,
            "note": "Minimal QWidget and qt_app import only; full Main and protocol connections not tested."}

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args(argv)
    report = run_smoke(timeout=args.timeout)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    return 0 if report["status"] == "passed" else 1

if __name__ == "__main__":
    sys.exit(main())
