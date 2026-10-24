
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
    # Relative "." is the SFTP account's initial working directory. Reject
    # traversal, control characters and ambiguous components for both forms.
    parts=directory.split('/')
    if directory.startswith('/'):
        parts=parts[1:]
        if directory != '/' and any(part in ('', '.', '..') for part in parts):
            raise ValueError('Chemin distant absolu non sûr')
    elif any(part in ('', '..') for part in parts) or directory.startswith('-'):
        raise ValueError('Chemin distant relatif non sûr')
    if any('\\' in part or any(ord(ch)<32 or ord(ch)==127 for ch in part) for part in parts):
        raise ValueError('Chemin distant non sûr')
    return posixpath.join(posixpath.normpath(directory),filename)

def local_entries(directory):
    root=Path(directory).expanduser()
    if not root.is_dir():raise ValueError('Répertoire local inexistant')
    return sorted([(p.name,p.is_dir()) for p in root.iterdir() if not p.is_symlink()],
                  key=lambda x:(not x[1],x[0].casefold()))

def remote_navigate(directory, entry):
    """Navigate a directory listing without escaping the relative account home."""
    if not isinstance(directory,str) or not directory:
        raise ValueError('Chemin distant requis')
    if not isinstance(entry,str) or not entry.endswith('/'):
        raise ValueError('Répertoire distant invalide')
    name=entry[:-1]
    if name != '..':
        return remote_child(directory,name)
    if any(ord(ch)<32 or ord(ch)==127 for ch in directory) or '\\' in directory:
        raise ValueError('Chemin distant non sûr')
    normalized=posixpath.normpath(directory)
    if normalized == '.':
        return '.'
    if not normalized.startswith('/'):
        if normalized == '..' or normalized.startswith('../'):
            raise ValueError('Chemin distant relatif non sûr')
        parent=posixpath.dirname(normalized)
        return parent if parent else '.'
    return posixpath.dirname(normalized) or '/'
