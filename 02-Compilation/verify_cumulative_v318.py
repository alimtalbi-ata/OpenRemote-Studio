#!/usr/bin/env python3
"""V31.8 ZIP release integrity gate. Author: Abdelhalim Talbi.

Checks structure, archive safety and provenance; does not certify Windows runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

REQUIRED = ("01-Application/", "02-Compilation/", "03-Sources/",
            "04-Tests-et-Qualification/", "05-Documentation/",
            "06-Historique/", "07-Manifestes/")
SHA40 = re.compile(r"^[a-fA-F0-9]{40}$")
MAX_FILES = 20000
MAX_TOTAL = 8 * 1024**3
MAX_RATIO = 1000

def check_manifest(archive, names, manifest, prefix, errors):
    """Verify exact archived bytes; never trust a workspace-only manifest."""
    if manifest not in names:
        errors.append("missing manifest: " + manifest)
        return
    try:
        raw = archive.read(manifest)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("manifest too large")
        entries = {}
        for line in raw.decode("utf-8").splitlines():
            if not re.fullmatch(r"[a-f0-9]{64}  [^\r\n]+", line):
                raise ValueError("invalid manifest line")
            digest, name = line.split("  ", 1)
            full = prefix + name
            if full in entries:
                raise ValueError("duplicate manifest path")
            entries[full] = digest
        expected = {n for n in names if n.startswith(prefix) and not n.endswith("/")
                    and n != manifest}
        if set(entries) != expected:
            raise ValueError("manifest file set mismatch")
        for name, expected_digest in entries.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected_digest:
                raise ValueError("manifest checksum mismatch: " + name)
    except (KeyError, UnicodeError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        errors.append("invalid manifest " + manifest + ": " + str(exc))

def verify(path, expected_commit=None):
    errors = []
    if not path.is_file():
        return {"archive": str(path), "sha256": None, "status": "FAIL",
                "errors": ["archive missing"]}
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(infos) > MAX_FILES:
                errors.append("too many ZIP entries")
            if len(names) != len(set(names)):
                errors.append("duplicate ZIP entry names")
            folded = [n.replace("\\", "/").casefold() for n in names]
            if len(folded) != len(set(folded)):
                errors.append("case-insensitive ZIP name collision")
            if sum(i.file_size for i in infos) > MAX_TOTAL:
                errors.append("uncompressed size limit exceeded")
            for info in infos:
                name = info.filename
                normalized = name.replace("\\", "/")
                parts = normalized.split("/")
                if (not name or normalized.startswith("/") or
                    "\\" in name or ".." in parts or "." in parts or
                    ":" in parts[0] or any(p.endswith((" ", ".")) for p in parts if p)):
                    errors.append("unsafe ZIP path: " + name)
                mode = info.external_attr >> 16
                if (mode & 0o170000) == 0o120000:
                    errors.append("symlink not permitted: " + name)
                if info.file_size and info.file_size / max(1, info.compress_size) > MAX_RATIO:
                    errors.append("compression ratio exceeded: " + name)
            for prefix in REQUIRED:
                if not any(n.startswith(prefix) for n in names):
                    errors.append("missing directory: " + prefix)
            if not errors:
                corrupt = archive.testzip()
                if corrupt:
                    errors.append("corrupt ZIP entry: " + corrupt)
            if not errors:
                check_manifest(archive, names, "07-Manifestes/FILES-SHA256.txt", "", errors)
                check_manifest(archive, names, "03-Sources/07-Manifestes/FILES-SHA256.txt",
                               "03-Sources/", errors)
            provenance = "07-Manifestes/provenance.json"
            if provenance not in names:
                errors.append("missing provenance.json")
            else:
                try:
                    data = json.loads(archive.read(provenance))
                    commit = data.get("commit")
                    if not isinstance(commit, str) or not SHA40.fullmatch(commit):
                        errors.append("invalid provenance commit")
                    if expected_commit and commit != expected_commit:
                        errors.append("source commit mismatch")
                    if not str(data.get("windows_build_run", "")).strip():
                        errors.append("missing Windows build run identifier")
                except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
                    errors.append("invalid provenance JSON: " + str(exc))
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError) as exc:
        errors.append("unreadable archive: " + str(exc))
    return {"archive": str(path), "sha256": digest,
            "status": "PASS" if not errors else "FAIL", "errors": errors}

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
