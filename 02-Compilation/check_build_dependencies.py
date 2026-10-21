"""Fail-closed audit of the Windows packaging environment.

Run with the build venv's Python. Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import importlib.metadata as metadata
import json
import platform
import struct
import sys

REQUIRED = ("PySide6", "paramiko", "cryptography", "pyinstaller")


def audit():
    result = {"python": sys.version.split()[0], "platform": platform.platform(), "bits": struct.calcsize("P") * 8, "dependencies": {}}
    for package in REQUIRED:
        try:
            result["dependencies"][package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            result["dependencies"][package] = None
    if sys.platform != "win32" or result["bits"] != 64:
        raise RuntimeError("Native Windows x64 Python is required")
    if sys.version_info < (3, 11):
        raise RuntimeError("Python >= 3.11 required")
    missing = [name for name, version in result["dependencies"].items() if not version]
    if missing:
        raise RuntimeError("Missing build dependencies: " + ", ".join(missing))
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(audit(), indent=2, sort_keys=True))
    except RuntimeError as exc:
        print("DEPENDENCY AUDIT FAILED:", exc, file=sys.stderr)
        raise SystemExit(1)
