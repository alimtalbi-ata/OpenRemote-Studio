
"""Atomic local download publication; preserves existing files on failed transfers.
Author: Abdelhalim Talbi.
"""
import os
import tempfile
import stat
import sys
from pathlib import Path

def download_atomic(sftp,remote_path,local_path,callback=None,cancelled=None):
    if cancelled is not None and cancelled():
        raise InterruptedError("Téléchargement annulé")
    target=Path(local_path)
    if target.is_symlink():
        raise ValueError('Destination symbolique interdite')
    if not target.parent.is_dir():
        raise FileNotFoundError("Répertoire local introuvable")
    fd,tmp=tempfile.mkstemp(prefix=".openremote-",suffix=".part",dir=str(target.parent))
    os.close(fd)
    try:
        sftp.get(remote_path,tmp,callback=callback)
        if cancelled is not None and cancelled():
            raise InterruptedError("Téléchargement annulé avant publication")
        if target.is_symlink():
            raise ValueError('Destination symbolique interdite avant publication')
        os.replace(tmp,target)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass

def remote_exists(sftp,path):
    try:
        sftp.stat(path)
        return True
    except FileNotFoundError:
        return False


def upload_exclusive(sftp, local_path, remote_path, callback=None, chunk_size=256*1024, cancelled=None):
    """Create a remote file exclusively, never overwrite an existing path.

    Requires server support for SSH_FXF_EXCL (Paramiko 'wbx' mode). On error,
    a newly created incomplete file is removed on a best-effort basis.
    """
    if not isinstance(chunk_size,int) or chunk_size<1 or chunk_size>16*1024*1024:
        raise ValueError("Taille de bloc invalide")
    source=Path(local_path)
    total=source.stat().st_size
    written=0
    created=False
    if cancelled is not None and cancelled():
        raise InterruptedError('Upload cancelled before remote creation')
    try:
        with source.open('rb') as local:
            with sftp.open(remote_path,'wbx') as remote:
                created=True
                while True:
                    if cancelled is not None and cancelled():
                        raise InterruptedError('Upload cancelled')
                    data=local.read(chunk_size)
                    if not data:break
                    remote.write(data)
                    written+=len(data)
                    if callback:callback(written,total)
                    if cancelled is not None and cancelled():
                        raise InterruptedError('Upload cancelled')
        return written
    except Exception:
        if created:
            try:sftp.remove(remote_path)
            except OSError:pass
        raise


import hashlib
import stat

def _download_resume_verified_unlocked(sftp, remote_path, local_path, identity, callback=None, chunk_size=256*1024, cancelled=None, lock_guard=None):
    """Resume to a stable .part, validating all existing bytes against remote.

    A changed remote prefix is rejected, not silently reused. Final size is
    checked before os.replace. Partial files are retained after interruption.
    """
    if not isinstance(chunk_size,int) or not 1<=chunk_size<=16*1024*1024:
        raise ValueError('Taille de bloc invalide')
    if cancelled is not None and cancelled():
        raise InterruptedError('Reprise annulée')
    if not isinstance(identity,str) or not identity:
        raise ValueError('Identité de connexion requise')
    if not isinstance(remote_path, str) or not remote_path:
        raise ValueError('Chemin distant requis')
    if not isinstance(local_path, (str, os.PathLike)):
        raise TypeError('Chemin local invalide')
    target=Path(local_path)
    if target.is_symlink():
        raise ValueError('Destination symbolique interdite')
    if not target.parent.is_dir():raise FileNotFoundError('Répertoire local introuvable')
    token=hashlib.sha256((identity+'\0'+remote_path+'\0'+str(target.resolve())).encode()).hexdigest()[:20]
    partial=target.parent/('.openremote-'+token+'.part')
    # Never append through a pre-existing symlink (including dangling links).
    if partial.is_symlink():
        raise ValueError('Fichier partiel symbolique interdit')
    if partial.exists() and not stat.S_ISREG(partial.stat().st_mode):
        raise ValueError('Fichier partiel non régulier interdit')
    initial_stat = sftp.stat(remote_path)
    remote_size = initial_stat.st_size
    if type(remote_size) is not int or remote_size < 0:
        raise ValueError('Taille distante invalide')
    total = remote_size
    have=partial.stat().st_size if partial.exists() else 0
    if have>total:raise ValueError('Fichier partiel plus grand que le fichier distant')
    # Reject changed remote metadata before validating the partial prefix.
    # Modification time is advisory: some SFTP servers provide only second precision.
    initial_mtime = getattr(initial_stat, 'st_mtime', None)
    initial_mode = getattr(initial_stat, 'st_mode', None)
    with sftp.open(remote_path,'rb') as remote:
        if have:
            with partial.open('rb') as existing:
                remaining=have
                while remaining:
                    if cancelled is not None and cancelled():
                        raise InterruptedError('Reprise annulée')
                    n=min(chunk_size,remaining)
                    a=existing.read(n);b=remote.read(n)
                    if len(a)!=n or a!=b:
                        raise ValueError('Fichier distant modifié : reprise refusée')
                    remaining-=n
        with partial.open('ab') as output:
            done=have
            if callback:callback(done,total)
            while done<total:
                if cancelled is not None and cancelled():
                    raise InterruptedError('Reprise annulée')
                data=remote.read(min(chunk_size,total-done))
                if not data:raise OSError('Fin prématurée du fichier distant')
                output.write(data);done+=len(data)
                if callback:callback(done,total)
            output.flush();os.fsync(output.fileno())
    if cancelled is not None and cancelled():
        raise InterruptedError('Reprise annulée')
    if partial.stat().st_size!=total:raise OSError('Taille de transfert incorrecte')
    # Re-stat before publishing: refuse a file whose size changed during
    # transfer, even when all downloaded chunks appeared valid.
    final_stat = sftp.stat(remote_path)
    final_size = final_stat.st_size
    if type(final_size) is not int or final_size != total:
        raise ValueError('Fichier distant modifié pendant le transfert')
    final_mtime = getattr(final_stat, 'st_mtime', None)
    if initial_mtime is not None and final_mtime is not None and final_mtime != initial_mtime:
        raise ValueError('Horodatage distant modifié pendant le transfert')
    final_mode = getattr(final_stat, 'st_mode', None)
    if initial_mode is not None and final_mode is not None and final_mode != initial_mode:
        raise ValueError('Type ou permissions du fichier distant modifiés pendant le transfert')
    if cancelled is not None and cancelled():
        raise InterruptedError('Reprise annulée avant publication')
    if target.is_symlink():
        raise ValueError('Destination symbolique interdite avant publication')
    # A replaced or removed lock invalidates exclusive ownership.
    if lock_guard is not None:
        lock_guard()
    os.replace(partial,target)
    return total


def download_resume_verified(sftp, remote_path, local_path, identity, callback=None, chunk_size=256*1024, cancelled=None):
    """Serialize concurrent resumes of the same connection/path/target.

    A lock is acquired with atomic exclusive creation. A stale lock is never
    removed automatically: doing so could corrupt an active transfer.
    """
    if not isinstance(chunk_size, int) or not 1 <= chunk_size <= 16*1024*1024:
        raise ValueError('Taille de bloc invalide')
    if cancelled is not None and cancelled():
        raise InterruptedError('Reprise annulée avant verrouillage')
    if not isinstance(identity, str) or not identity:
        raise ValueError('Identité de connexion requise')
    if not isinstance(remote_path, str) or not remote_path:
        raise ValueError('Chemin distant requis')
    if not isinstance(local_path, (str, os.PathLike)):
        raise TypeError('Chemin local invalide')
    target = Path(local_path)
    if target.is_symlink():
        raise ValueError('Destination symbolique interdite')
    if not target.parent.is_dir():
        raise FileNotFoundError('Répertoire local introuvable')
    token = hashlib.sha256((identity+'\0'+remote_path+'\0'+str(target.resolve())).encode()).hexdigest()[:20]
    lock = target.parent / ('.openremote-' + token + '.lock')
    try:
        fd = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except FileExistsError as exc:
        raise RuntimeError('Reprise déjà en cours ou verrou résiduel : ' + str(lock)) from exc
    try:
        owned = os.fstat(fd)
        if not stat.S_ISREG(owned.st_mode):
            raise ValueError('Verrou de reprise non régulier')
        # Cross-platform ownership marker: Windows may expose different
        # file identity metadata via fstat and path stat.
        owned_identity = (owned.st_dev, owned.st_ino) if os.name != 'nt' else None
        marker = os.urandom(32)
        if os.write(fd, marker) != len(marker):
            raise OSError('Écriture du marqueur de verrou incomplète')
        os.fsync(fd)
    finally:
        os.close(fd)

    def assert_lock_owner():
        try:
            fd_check = os.open(str(lock), os.O_RDONLY |
                               getattr(os, 'O_BINARY', 0) |
                               getattr(os, 'O_NOFOLLOW', 0))
        except FileNotFoundError as exc:
            raise RuntimeError('Verrou de reprise disparu avant publication') from exc
        except OSError as exc:
            raise RuntimeError('Verrou de reprise inaccessible avant publication') from exc
        try:
            current = os.fstat(fd_check)
            if (not stat.S_ISREG(current.st_mode) or
                    (owned_identity is not None and
                     (current.st_dev, current.st_ino) != owned_identity) or
                    os.read(fd_check, len(marker) + 1) != marker):
                raise RuntimeError('Verrou de reprise remplacé avant publication')
        finally:
            os.close(fd_check)

    try:
        return _download_resume_verified_unlocked(sftp, remote_path, local_path, identity,
                                                   callback=callback, chunk_size=chunk_size,
                                                   cancelled=cancelled, lock_guard=assert_lock_owner)
    finally:
        # Best effort: not an atomic compare-and-unlink. Preserve replacement locks.
        active_error = sys.exc_info()[0] is not None
        try:
            assert_lock_owner()
        except RuntimeError:
            if not active_error:
                raise
        else:
            lock.unlink()
