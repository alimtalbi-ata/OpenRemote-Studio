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

def reconcile_archive_source_manifest(files):
    """Hash the exact archived source bytes, not untracked CI workspace files.

    The workspace manifest may include generated DOCX/PDF files absent from
    git ls-files or stale installer metadata. Rebuild only the archived copy.
    """
    prefix = "03-Sources/"
    manifest = prefix + "07-Manifestes/FILES-SHA256.txt"
    entries = sorted((name[len(prefix):], data) for name, data in files.items()
                     if name.startswith(prefix) and name != manifest)
    files[manifest] = ("\n".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}" for name, data in entries
    ) + "\n").encode("utf-8")
    return len(entries)

UI_CAPTURE_NAMES = (
    "qt-zabbix-r109-offline.png",
    "qt-zabbix-r110-consent-revoked.png",
    "qt-grafana-r114-offline.png",
)
PNG_SIGNATURE = bytes((137, 80, 78, 71, 13, 10, 26, 10))


def collect_required_ui_captures(qualification_dir):
    """Collect only named, generated Qt evidence and fail if a capture is absent."""
    directory = Path(qualification_dir)
    captures = []
    for name in UI_CAPTURE_NAMES:
        path = directory / name
        if not path.is_file():
            raise SystemExit(f"Missing required Qt UI capture: {name}")
        data = path.read_bytes()
        if len(data) < 128 or not data.startswith(PNG_SIGNATURE):
            raise SystemExit(f"Invalid Qt UI capture: {name}")
        captures.append((name, data))
    return captures


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
            if name.startswith(("02-Compilation/", "04-Tests-et-Qualification/", "05-Documentation/")):
                add(name, path.read_bytes())
    # R104: source manifest describes the archived snapshot, not untracked
    # generated workspace docs or pre-build installer metadata.
    source_count = reconcile_archive_source_manifest(files)
    print(f"Reconciled archived source manifest: {source_count} source files")
    add("01-Application/Installer/" + installer.name, installer.read_bytes())
    add("01-Application/Portable/" + portable.name, portable.read_bytes())
    for path in docs:
        add("05-Documentation/" + path.name, path.read_bytes())
    for path in (ROOT / "Binary" / "Qualification").glob("*.json"):
        add("04-Tests-et-Qualification/" + path.name, path.read_bytes())
    ui_captures = collect_required_ui_captures(ROOT / "Binary" / "Qualification")
    for name, data in ui_captures:
        add("04-Tests-et-Qualification/" + name, data)
    print("Included offline Qt UI evidence: " + ", ".join(name for name, _ in ui_captures))
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
