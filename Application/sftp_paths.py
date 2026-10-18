
"""SFTP path planning, kept separate from Qt. Author: Abdelhalim Talbi."""
import posixpath
from pathlib import Path

def remote_child(directory, filename):
    if not isinstance(filename,str) or not filename or filename in ('.','..'):
        raise ValueError('Nom de fichier invalide')
    if '/' in filename or '\\' in filename or any(ord(c)<32 or ord(c)==127 for c in filename):
        raise ValueError('Nom de fichier non sûr')
    if not isinstance(directory,str) or not directory.startswith('/'):
        raise ValueError('Chemin distant absolu requis')
    return posixpath.join(posixpath.normpath(directory),filename)

def local_entries(directory):
    root=Path(directory).expanduser()
    if not root.is_dir():raise ValueError('Répertoire local inexistant')
    return sorted([(p.name,p.is_dir()) for p in root.iterdir() if not p.is_symlink()],
                  key=lambda x:(not x[1],x[0].casefold()))
