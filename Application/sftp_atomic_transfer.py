"""Publish a completed SFTP download atomically; discard cancelled partial data."""
import os
from pathlib import Path
import tempfile

class TransferCancelled(RuntimeError):
    pass

def download_atomic(sftp, remote, destination, cancelled=lambda: False):
    """Never overwrite destination until download completes and cancellation is checked."""
    destination = Path(destination)
    if cancelled():
        raise TransferCancelled('download cancelled before start')
    fd, temporary = tempfile.mkstemp(prefix='.' + destination.name + '.', suffix='.partial', dir=destination.parent)
    os.close(fd)
    try:
        sftp.get(remote, temporary)
        if cancelled():
            raise TransferCancelled('download cancelled before publication')
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
