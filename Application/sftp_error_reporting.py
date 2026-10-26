"""Safe, stable SFTP failure messages. Never serialize exception payloads.
Author: Abdelhalim Talbi.
"""
import errno
import socket


def _safe_errno(exc):
    """Read only an integer errno; tolerate custom exception objects."""
    try:
        value = exc.errno
    except Exception:
        return None
    return value if type(value) is int else None


def safe_sftp_error_message(exc):
    """Return a non-sensitive message without calling str(exc) or repr(exc)."""
    code = _safe_errno(exc)
    if isinstance(exc, (TimeoutError, socket.timeout)) or code == errno.ETIMEDOUT:
        return "Le délai de l’opération SSH/SFTP a expiré."
    if isinstance(exc, PermissionError) or code in (errno.EACCES, errno.EPERM):
        return "Accès SSH/SFTP refusé."
    if isinstance(exc, FileNotFoundError) or code == errno.ENOENT:
        return "Fichier ou chemin SSH/SFTP introuvable."
    interrupted_codes = {
        errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE,
        getattr(errno, "ENETRESET", errno.ECONNRESET),
    }
    if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)) or code in interrupted_codes:
        return "La connexion SSH/SFTP a été interrompue."
    unavailable_codes = {errno.ECONNREFUSED, errno.ENETUNREACH, errno.EHOSTUNREACH}
    if isinstance(exc, ConnectionError) or code in unavailable_codes:
        return "Connexion SSH/SFTP impossible."
    if isinstance(exc, (ValueError, TypeError)):
        return "Paramètres de l’opération SFTP invalides."
    return "Échec de l’opération SFTP. Détails techniques masqués."
