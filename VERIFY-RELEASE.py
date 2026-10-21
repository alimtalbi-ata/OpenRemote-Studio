#!/usr/bin/env python3
"""Validate current cumulative source tree and archive, without historical paths."""
from pathlib import Path
import hashlib, sys, zipfile

REQUIRED = ('VERSION.txt', 'README.md', 'Application/qt_app.py', '02-Compilation/QUALIFIER-ET-CONSTRUIRE-WINDOWS.cmd', )
MANIFEST = '07-Manifestes/FILES-SHA256.txt'

def _checks(read, names):
    errors=[]
    version=read('VERSION.txt').decode('utf-8').strip() if 'VERSION.txt' in names else ''
    required=REQUIRED + (f'05-Documentation/Dossier-V{version}.docx', f'05-Documentation/Dossier-V{version}.pdf')
    for name in required:
        if name not in names: errors.append('Fichier requis absent: '+name)
    if MANIFEST not in names: return errors+['Manifeste absent: '+MANIFEST]
    seen=set()
    for line in read(MANIFEST).decode('utf-8').splitlines():
        if not line.strip(): continue
        try: digest,name=line.split('  ',1)
        except ValueError: errors.append('Ligne manifeste invalide'); continue
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): errors.append('Empreinte invalide: '+name); continue
        if name in seen: errors.append('Entrée manifeste dupliquée: '+name); continue
        seen.add(name)
        if name not in names: errors.append('Fichier manifesté absent: '+name); continue
        if hashlib.sha256(read(name)).hexdigest()!=digest: errors.append('Empreinte invalide: '+name)
    expected={n for n in names if not n.endswith('/') and n!=MANIFEST}
    errors.extend('Non référencé: '+n for n in sorted(expected-seen))
    errors.extend('Entrée manifeste interdite: '+n for n in sorted(seen-expected))
    return errors

def validate(root):
    root=Path(root)
    metadata={'.git','__pycache__','.pytest_cache','.venv','.venv-build','dist','build'}
    names={p.relative_to(root).as_posix() for p in root.rglob('*')
           if p.is_file() and not metadata.intersection(p.relative_to(root).parts)
           and not (p.relative_to(root).as_posix().startswith('Binary/') and
                    (p.name.endswith('.log') or p.name == '.windows-build.lock' or
                     '/Qualification/' in p.relative_to(root).as_posix()))}
    return _checks(lambda n:(root/n).read_bytes(),names)

def validate_archive(path):
    try:
        with zipfile.ZipFile(path) as z:
            names=z.namelist(); errors=[]
            if len(names)!=len(set(names)): errors.append('Entrée ZIP dupliquée')
            if any(n.startswith('/') or '..' in Path(n).parts or '\\' in n for n in names): errors.append('Chemin ZIP non sûr')
            if z.testzip(): errors.append('Archive corrompue')
            errors+=_checks(z.read,set(names))
            return errors
    except (OSError,zipfile.BadZipFile,KeyError,UnicodeDecodeError) as exc: return ['Archive invalide: '+str(exc)]

if __name__=='__main__':
    issues=validate_archive(sys.argv[1]) if len(sys.argv)>1 and sys.argv[1].endswith('.zip') else validate(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent)
    for issue in issues: print('BLOCK:',issue)
    if not issues: print('PASS: release integrity')
    raise SystemExit(bool(issues))
