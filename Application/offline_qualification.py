"""Safe offline qualification; no GUI, network or credential access.
Author: Abdelhalim Talbi.
"""
import ast
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from qualification_matrix import build_matrix

CHECKS = (
    ("OFF-SOURCE", "Static source inventory"),
    ("OFF-ENTRY", "Application entrypoint syntax"),
    ("OFF-TESTS", "Python unittest regression suite"),
)

def _parse_entrypoint(root):
    path = Path(root) / "app.py"
    if not path.is_file():
        return False, "entrypoint_missing"
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename="app.py")
    except (OSError, UnicodeError, SyntaxError):
        return False, "entrypoint_invalid"
    return True, "entrypoint_parsed"

def run_offline(root, *, run_tests=False, timeout=180):
    root = Path(root)
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise ValueError("timeout must be an integer from 1 to 600")
    report = build_matrix(root)
    inventory = report["source_inventory"]
    source_ok = all(item["source_ready"] for item in inventory.values())
    entry_ok, entry_reason = _parse_entrypoint(root)
    checks = [
        {"id": "OFF-SOURCE", "status": "passed" if source_ok else "failed", "detail": "source_inventory_checked"},
        {"id": "OFF-ENTRY", "status": "passed" if entry_ok else "failed", "detail": entry_reason},
    ]
    if not run_tests:
        checks.append({"id": "OFF-TESTS", "status": "not_executed", "detail": "requires_explicit_opt_in"})
    else:
        try:
            result = subprocess.run([sys.executable, "-W", "error::ResourceWarning", "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
            checks.append({"id": "OFF-TESTS", "status": "passed" if result.returncode == 0 else "failed", "detail": "unittest_exit_" + str(result.returncode)})
        except subprocess.TimeoutExpired:
            checks.append({"id": "OFF-TESTS", "status": "failed", "detail": "unittest_timeout"})
        except OSError:
            checks.append({"id": "OFF-TESTS", "status": "failed", "detail": "unittest_launch_failed"})
    report["offline_checks"] = checks
    report["offline_checks_passed"] = sum(c["status"] == "passed" for c in checks)
    report["offline_checks_failed"] = sum(c["status"] == "failed" for c in checks)
    report["qualification_note"] = "Offline checks only. Windows GUI and live protocol scenarios not executed."
    return report

def write_offline_report(root, destination, *, run_tests=False, timeout=180):
    path = Path(destination)
    if path.exists():
        raise FileExistsError("Refusing to overwrite qualification report")
    report = run_offline(root, run_tests=run_tests, timeout=timeout)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Offline qualification; never claims Windows or live protocol validation")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-tests", action="store_true", help="Run the local unittest regression suite")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    write_offline_report(args.root, args.output, run_tests=args.run_tests, timeout=args.timeout)
