#!/usr/bin/env python3
"""V31.8 cumulative release verifier. Author: Abdelhalim Talbi.

Verify a ZIP without extracting it. Optionally enforce a source commit and
required release folders. This is not a substitute for native Windows tests.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

REQUIRED = ("01-Application/", "02-Compilation/", "03-Sources/",
            "04-Tests-et-Qualification/", "05-Documentation/",
            "06-Historique/", "07-Manifestes/")

def verify(path, expected_commit=None):
    errors = []
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            errors.append("duplicate ZIP entry names")
        folded = [n.casefold() for n in names]
        if len(folded) != len(set(folded)):
            errors.append("case-insensitive ZIP name collision")
        for name in names:
            parts = name.replace("\\", "/").split("/")
            if name.startswith(("/", "\\")) or ".." in parts or ":" in parts[0]:
                errors.append("unsafe ZIP path: " + name)
            info = archive.getinfo(name)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                errors.append("symlink not permitted: " + name)
        for prefix in REQUIRED:
            if not any(n.startswith(prefix) for n in names):
                errors.append("missing directory: " + prefix)
        corrupt = archive.testzip()
        if corrupt:
            errors.append("corrupt ZIP entry: " + corrupt)
        provenance = "07-Manifestes/provenance.json"
        if provenance not in names:
            errors.append("missing provenance.json")
        else:
            try:
                data = json.loads(archive.read(provenance))
                if not isinstance(data.get("commit"), str) or len(data["commit"]) != 40:
                    errors.append("invalid provenance commit")
                if expected_commit and data.get("commit") != expected_commit:
                    errors.append("source commit mismatch")
                if not data.get("windows_build_run"):
                    errors.append("missing Windows build run identifier")
            except (ValueError, KeyError) as exc:
                errors.append("invalid provenance JSON: " + str(exc))
    return {"archive": str(path), "sha256": digest, "status": "PASS" if not errors else "FAIL", "errors": errors}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.archive, args.expected_commit)
    report = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
