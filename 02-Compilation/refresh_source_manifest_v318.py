#!/usr/bin/env python3
"""Regenerate source-tree integrity manifest from the checked-out commit.

CI-generated manifest is evidence of workspace bytes, not a Git commit itself.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import hashlib
import os
import sys

EXCLUDED = {".git", "__pycache__", ".pytest_cache", ".venv",
            ".venv-build", "dist", "build"}
MANIFEST = "07-Manifestes/FILES-SHA256.txt"

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if name == MANIFEST or EXCLUDED.intersection(path.relative_to(root).parts):
            continue
        if name.startswith("Binary/") and (name.endswith(".log") or
                path.name == ".windows-build.lock" or "/Qualification/" in name):
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}")
    target = root / MANIFEST
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(entries) + "\n", encoding="utf-8")
    print(f"Refreshed {MANIFEST}: {len(entries)} files")
    return 0

if __name__ == "__main__":
    sys.exit(main())
