"""Offline integration qualification matrix; no live protocol claims.
Author: Abdelhalim Talbi.
"""
import json
from pathlib import Path
from protocol_readiness import inspect_source

SCENARIOS = (
    ("WIN-LAUNCH", "Windows application startup", "Windows", "manual"),
    ("WIN-DPI", "DPI scaling at 100/150/200 percent", "Windows", "manual"),
    ("WIN-KEYBOARD", "Keyboard and focus navigation", "Windows", "manual"),
    ("SSH-DIRECT", "SSH direct authentication and host-key verification", "SSH", "live"),
    ("SSH-BASTION", "SSH chained bastions and cancellation", "SSH", "live"),
    ("RDP-GATEWAY", "RDP via Windows gateway", "RDP", "live"),
    ("VNC-SESSION", "VNC remote desktop session", "VNC", "live"),
    ("SFTP-TRANSFER", "SFTP upload/download and failure recovery", "SFTP", "live"),
    ("PAM-VAULT", "Password vault / PAM jump integration", "PAM", "live"),
)

def build_matrix(root):
    readiness = inspect_source(root)
    rows = []
    for ident, description, protocol, kind in SCENARIOS:
        static_ready = readiness.get(protocol, {}).get("source_ready") if protocol in readiness else None
        rows.append({"id": ident, "description": description, "protocol": protocol,
                     "validation": kind, "status": "not_executed", "static_source_ready": static_ready})
    return {"schema": "openremote-qualification-v1", "source_inventory": readiness,
            "scenarios": rows, "live_tests_executed": 0, "gui_tests_executed": 0}

def write_report(root, destination):
    path = Path(destination)
    if path.exists():
        raise FileExistsError("Refusing to overwrite qualification report")
    report = build_matrix(root)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create an offline qualification matrix; does not test real connections")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_report(args.root, args.output)
