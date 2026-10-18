#!/usr/bin/env python3
"""Cross-platform validation of Windows PE binaries and portable ZIP contents.

Structural validation only: does not prove executable compatibility or GUI startup.
"""
import argparse
import stat
import struct
import sys
import zipfile
from pathlib import Path, PurePosixPath


def valid_pe(data):
    if len(data) < 512 or data[:2] != b'MZ':
        return False
    offset = struct.unpack_from('<I', data, 0x3c)[0]
    return 64 <= offset <= len(data) - 24 and data[offset:offset+4] == b'PE\0\0' and struct.unpack_from('<H', data, offset+20)[0] > 0


def verify_installer(path):
    return [] if valid_pe(Path(path).read_bytes()) else ['Installer is not a structurally valid PE']


def verify_portable(path, onefile=False):
    errors = []
    with zipfile.ZipFile(path) as archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        names = [i.filename.replace('\\', '/') for i in infos]
        if len(names) != len(set(n.casefold() for n in names)):
            errors.append('Duplicate/case-colliding portable paths')
        for info in infos:
            name = info.filename
            parts = PurePosixPath(name).parts
            if (not name or name.startswith('/') or '\\' in name
                    or '..' in parts or '.' in parts or ':' in name
                    or any(part.endswith((' ', '.')) for part in parts)):
                errors.append('Unsafe path: ' + name)
            unix_mode = (info.external_attr >> 16) & 0xffff
            if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
                errors.append('Symlink not permitted: ' + name)
            if info.file_size > 2 * 1024**3:
                errors.append('Oversized member: ' + name)
            if info.file_size > 10 * 1024**2 and info.file_size > max(1, info.compress_size) * 1000:
                errors.append('Excessive compression ratio: ' + name)
        if sum(info.file_size for info in infos) > 4 * 1024**3:
            errors.append('Portable archive exceeds 4 GiB uncompressed')
        if archive.testzip() is not None:
            errors.append('Corrupt ZIP member')
        executables = [i for i in infos if PurePosixPath(i.filename).name.casefold() == 'openremotestudio.exe']
        if len(executables) != 1:
            errors.append('Expected exactly one OpenRemoteStudio.exe')
        elif not valid_pe(archive.read(executables[0])):
            errors.append('Portable executable is not a structurally valid PE')
        if not onefile:
            if len([n for n in names if n.lower().endswith('/platforms/qwindows.dll')]) != 1:
                errors.append('Missing/duplicated Qt platform plugin')
            if not any(PurePosixPath(n).name.lower().startswith('python3') and n.lower().endswith('.dll') for n in names):
                errors.append('Missing Python runtime DLL')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--portable', required=True, type=Path)
    parser.add_argument('--installer', type=Path)
    parser.add_argument('--onefile', action='store_true')
    args = parser.parse_args(argv)
    try:
        issues = verify_portable(args.portable, args.onefile)
        if args.installer:
            issues.extend(verify_installer(args.installer))
    except (OSError, ValueError, zipfile.BadZipFile, EOFError) as exc:
        issues = [str(exc)]
    for issue in issues:
        print('FAIL:', issue)
    if not issues:
        print('PASS: portable archive and PE structure')
    return int(bool(issues))


if __name__ == '__main__':
    sys.exit(main())
