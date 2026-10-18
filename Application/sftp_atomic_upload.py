"""Stage SFTP uploads remotely and publish only with an atomic POSIX rename.

Servers without posix_rename are deliberately unsupported: plain rename may
reject existing targets or have non-atomic replacement semantics.
"""
import posixpath
import secrets
from sftp_atomic_transfer import TransferCancelled


def upload_atomic(sftp, source, destination, cancelled=lambda: False):
    """Upload to a sibling temporary path, then atomically publish if supported.

    Cancellation is cooperative; a network call already in progress may block.
    A failed best-effort cleanup is not silently treated as success.
    """
    if cancelled():
        raise TransferCancelled('upload cancelled before start')
    if not callable(getattr(sftp, 'posix_rename', None)):
        raise RuntimeError('server/client lacks POSIX atomic rename; upload not started')
    destination = str(destination)
    folder, filename = posixpath.split(destination)
    if not filename or filename in ('.', '..'):
        raise ValueError('invalid remote destination')
    temporary = posixpath.join(folder, '.' + filename + '.' + secrets.token_hex(12) + '.partial')
    try:
        sftp.put(str(source), temporary)
        if cancelled():
            raise TransferCancelled('upload cancelled before publication')
        sftp.posix_rename(temporary, destination)
    except BaseException as original:
        try:
            sftp.remove(temporary)
        except Exception as cleanup_error:
            original.add_note('remote temporary cleanup failed for this transfer: ' + str(cleanup_error))
        raise
