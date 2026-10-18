"""Offline readiness inventory for OpenRemote Studio. No network calls.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import ast

MODULES = {
    "SSH": ("ssh_route_client.py", "ssh_end_to_end_probe.py", "ssh_path_editor.py"),
    "RDP": ("rdp_sessions.py", "gateways.py"),
    "SFTP": ("sftp_paths.py", "qt_workers.py"),
    "VNC": ("gateways.py", "qt_app.py"),
}

def inspect_source(root):
    """Static module/parse inventory; does not imply functional protocol validation."""
    root = Path(root)
    result = {}
    for protocol, names in MODULES.items():
        details = []
        for name in names:
            file = root / name
            if not file.is_file():
                details.append({"module": name, "status": "missing"})
                continue
            try:
                source = file.read_text(encoding="utf-8")
                ast.parse(source, filename=name)
            except (OSError, UnicodeError, SyntaxError):
                details.append({"module": name, "status": "invalid"})
            else:
                details.append({"module": name, "status": "parsed"})
        result[protocol] = {"modules": details, "source_ready": all(d["status"] == "parsed" for d in details)}
    return result

def summary(report):
    if not isinstance(report, dict) or set(report) != set(MODULES):
        raise ValueError("Invalid readiness report")
    return {"source_ready": sum(bool(report[p]["source_ready"]) for p in MODULES),
            "protocols_checked": len(MODULES),
            "qualification": "static-source-only"}
