"""Read-only Windows GUI readiness assessment; no application launch. Author: Abdelhalim Talbi."""
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path

REQUIRED = ("PySide6",)
OPTIONAL = ("paramiko",)

def assess(root, *, system=None, find_spec=None):
    root = Path(root)
    system = platform.system() if system is None else system
    find_spec = importlib.util.find_spec if find_spec is None else find_spec
    dependencies = {}
    for module in REQUIRED + OPTIONAL:
        try:
            present = find_spec(module) is not None
        except (ImportError, ValueError, AttributeError):
            present = False
        dependencies[module] = {"installed": present, "required": module in REQUIRED}
    entry = root / "app.py"
    source_present = entry.is_file()
    ready = system == "Windows" and source_present and all(dependencies[m]["installed"] for m in REQUIRED)
    return {"schema": "openremote.windows-preflight.v1", "platform": system,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "entrypoint_present": source_present, "dependencies": dependencies,
            "ready_to_attempt_gui_launch": ready,
            "gui_launch_executed": False, "live_protocol_tests_executed": False,
            "note": "Read-only preflight; readiness is not GUI or protocol validation."}

def write_report(root, destination):
    path = Path(destination)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(assess(root), stream, indent=2)
        stream.write("\n")
    return path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Windows readiness check without GUI launch")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_report(args.root, args.output)
