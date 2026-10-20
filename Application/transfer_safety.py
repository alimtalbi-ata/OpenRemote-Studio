
"""Atomic local download publication; preserves existing files on failed transfers.
Author: Abdelhalim Talbi.
"""
import os
import tempfile
from pathlib import Path

def download_atomic(sftp,remote_path,local_path,callback=None,cancelled=None):
    if cancelled is not None and cancelled():
        raise InterruptedError("Téléchargement annulé")
    target=Path(local_path)
    if not target.parent.is_dir():
        raise FileNotFoundError("Répertoire local introuvable")
    fd,tmp=tempfile.mkstemp(prefix=".openremote-",suffix=".part",dir=str(target.parent))
    os.close(fd)
    try:
        sftp.get(remote_path,tmp,callback=callback)
        if cancelled is not None and cancelled():
            raise InterruptedError("Téléchargement annulé avant publication")
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

    Requires server support for SSH_FXF_EXCL (Paramiko 'x' mode). On error,
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
            with sftp.open(remote_path,'xb') as remote:
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

def download_resume_verified(sftp, remote_path, local_path, identity, callback=None, chunk_size=256*1024, cancelled=None):
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
    remote_size = sftp.stat(remote_path).st_size
    if type(remote_size) is not int or remote_size < 0:
        raise ValueError('Taille distante invalide')
    total = remote_size
    have=partial.stat().st_size if partial.exists() else 0
    if have>total:raise ValueError('Fichier partiel plus grand que le fichier distant')
    # Reject changed remote metadata before validating the partial prefix.
    # Modification time is advisory: some SFTP servers provide only second precision.
    initial_stat = sftp.stat(remote_path)
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
    final_size = sftp.stat(remote_path).st_size
    if type(final_size) is not int or final_size != total:
        raise ValueError('Fichier distant modifié pendant le transfert')
    final_stat = sftp.stat(remote_path)
    final_mtime = getattr(final_stat, 'st_mtime', None)
    if initial_mtime is not None and final_mtime is not None and final_mtime != initial_mtime:
        raise ValueError('Horodatage distant modifié pendant le transfert')
    final_mode = getattr(final_stat, 'st_mode', None)
    if initial_mode is not None and final_mode is not None and final_mode != initial_mode:
        raise ValueError('Type ou permissions du fichier distant modifiés pendant le transfert')
    if cancelled is not None and cancelled():
        raise InterruptedError('Reprise annulée avant publication')
    os.replace(partial,target)
    return total
