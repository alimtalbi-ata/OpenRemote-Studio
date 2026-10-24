
"""SFTP path planning, kept separate from Qt. Author: Abdelhalim Talbi."""
import posixpath
from pathlib import Path

def remote_child(directory, filename):
    if not isinstance(filename,str) or not filename or filename in ('.','..'):
        raise ValueError('Nom de fichier invalide')
    if '/' in filename or '\\' in filename or any(ord(c)<32 or ord(c)==127 for c in filename):
        raise ValueError('Nom de fichier non sûr')
    if not isinstance(directory,str) or not directory:
        raise ValueError('Chemin distant requis')
    # Relative "." is the SFTP account's initial working directory. Keep
    # relative paths relative; reject traversal and ambiguous components.
    if not directory.startswith('/'):
        parts=directory.split('/')
        if any(part in ('', '..') for part in parts) or directory.startswith('-'):
            raise ValueError('Chemin distant relatif non sûr')
        if any('\\' in part or any(ord(ch)<32 or ord(ch)==127 for ch in part) for part in parts):
            raise ValueError('Chemin distant relatif non sûr')
    return posixpath.join(posixpath.normpath(directory),filename)

def local_entries(directory):
    root=Path(directory).expanduser()
    if not root.is_dir():raise ValueError('Répertoire local inexistant')
    return sorted([(p.name,p.is_dir()) for p in root.iterdir() if not p.is_symlink()],
                  key=lambda x:(not x[1],x[0].casefold()))
