#!/usr/bin/env python3
"""Assemble a single cumulative Windows ZIP from a successful CI workspace.

The archive contains actual build outputs and tracked sources at HEAD.
Author: Abdelhalim Talbi.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
RELEASE = ROOT / "Binary" / f"V{VERSION}"
OUTPUT = ROOT / "Binary" / f"OpenRemote-Studio-V{VERSION}-Windows-Cumulative.zip"
SECTIONS = ("01-Application/", "02-Compilation/", "03-Sources/",
            "04-Tests-et-Qualification/", "05-Documentation/",
            "06-Historique/", "07-Manifestes/")

def main():
    if VERSION != "31.8":
        raise SystemExit(f"Wrong release version: {VERSION}")
    installer = RELEASE / "Installer" / f"OpenRemoteStudio-V{VERSION}-Windows-Setup.exe"
    portable = RELEASE / "Portable" / f"OpenRemoteStudio-V{VERSION}-Windows-Portable.zip"
    for file in (installer, portable):
        if not file.is_file() or file.stat().st_size < 1024:
            raise SystemExit(f"Missing native artifact: {file}")
    docs = [ROOT / "05-Documentation" / f"Dossier-V{VERSION}.{ext}" for ext in ("docx", "pdf")]
    for file in docs:
        if not file.is_file():
            raise SystemExit(f"Missing versioned document: {file}")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if len(sha) != 40:
        raise SystemExit("Invalid source SHA")
    run_id = __import__("os").environ.get("GITHUB_RUN_ID", "").strip()
    if not run_id:
        raise SystemExit("Missing GitHub Actions run ID")
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    files = {}
    def add(name, data):
        if name in files:
            raise SystemExit(f"Duplicate archive path: {name}")
        files[name] = data
    for name in sorted(filter(None, names)):
        path = ROOT / name
        if path.is_file():
            add("03-Sources/" + name, path.read_bytes())
    add("01-Application/Installer/" + installer.name, installer.read_bytes())
    add("01-Application/Portable/" + portable.name, portable.read_bytes())
    for path in docs:
        add("05-Documentation/" + path.name, path.read_bytes())
    for path in (ROOT / "Binary" / "Qualification").glob("*.json"):
        add("04-Tests-et-Qualification/" + path.name, path.read_bytes())
    for path in (ROOT / "Binary").glob("build-*.log"):
        add("04-Tests-et-Qualification/" + path.name, path.read_bytes())
    add("06-Historique/VERSION.txt", (VERSION + "\n").encode())
    provenance = {"commit": sha, "windows_build_run": run_id, "version": VERSION,
                  "source": "GitHub Actions checkout", "author": "Abdelhalim Talbi"}
    add("07-Manifestes/provenance.json", (json.dumps(provenance, indent=2) + "\n").encode())
    digest_lines = [f"{hashlib.sha256(data).hexdigest()}  {name}"
                    for name, data in sorted(files.items())]
    add("07-Manifestes/FILES-SHA256.txt", ("\n".join(digest_lines) + "\n").encode())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                         allowZip64=True) as archive:
        for section in SECTIONS:
            archive.writestr(section, b"")
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    print(f"Created {OUTPUT.name}: {OUTPUT.stat().st_size} bytes; {len(files)} files")
    return 0

if __name__ == "__main__":
    sys.exit(main())
