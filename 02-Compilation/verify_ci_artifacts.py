"""Validate Windows build artifacts without accepting placeholders.

This script is intentionally independent from PySide6 and can run in CI.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
import zipfile


def verify(root: pathlib.Path) -> list[tuple[str, str]]:
    version = (root / "VERSION.txt").read_text(encoding="utf-8").strip()
    if not version or any(ch not in "0123456789." for ch in version):
        raise ValueError("Invalid VERSION.txt")
    release = root / "Binary" / f"V{version}"
    installer = release / "Installer" / f"OpenRemoteStudio-V{version}-Windows-Setup.exe"
    portable = release / "Portable" / f"OpenRemoteStudio-V{version}-Windows-Portable.zip"
    for path in (installer, portable):
        if not path.is_file() or path.stat().st_size < 1024:
            raise ValueError(f"Missing or empty artifact: {path}")
    with installer.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise ValueError("Installer is not a Windows PE executable")
    with zipfile.ZipFile(portable) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt portable archive")
        entries = [name for name in archive.namelist() if name.lower().endswith(".exe")]
        if not entries:
            raise ValueError("Portable archive does not contain an executable")
        if any(name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts for name in archive.namelist()):
            raise ValueError("Unsafe portable archive paths")
    return [(str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest()) for path in (installer, portable)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        for name, digest in verify(args.root):
            print(f"SHA256 {digest}  {name}")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
