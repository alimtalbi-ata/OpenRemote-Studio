"""Stable, non-sensitive messages for TCP connectivity probes.

Exception payloads can contain private host strings or adapter-supplied data.
This module deliberately maps errors to fixed text and never stringifies them.
Author: Abdelhalim Talbi.
"""
import errno
import socket


def _safe_errno(exc):
    """Read only an integer errno; custom exception properties may be hostile."""
    try:
        value = exc.errno
    except Exception:
        return None
    return value if type(value) is int else None


def _matches_errno(code, *names):
    if code is None:
        return False
    return any(getattr(errno, name, object()) == code for name in names)


def safe_tcp_error_message(exc):
    """Return an actionable, fixed message without using str(exc) or repr(exc)."""
    if isinstance(exc, socket.gaierror):
        return "Résolution du nom impossible."

    code = _safe_errno(exc)
    if (isinstance(exc, (TimeoutError, socket.timeout))
            or _matches_errno(code, "ETIMEDOUT")):
        return "Délai de connexion dépassé."

    if (isinstance(exc, ConnectionRefusedError)
            or _matches_errno(code, "ECONNREFUSED")):
        return "Connexion refusée par la cible (port fermé ou service arrêté)."

    if (isinstance(exc, PermissionError)
            or _matches_errno(code, "EACCES", "EPERM")):
        return "Connexion refusée par la politique locale."

    if _matches_errno(code, "ENETUNREACH", "EHOSTUNREACH", "ENETDOWN", "EHOSTDOWN"):
        return "Hôte ou réseau injoignable."

    if (isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError))
            or _matches_errno(code, "ECONNRESET", "ECONNABORTED", "EPIPE")):
        return "Connexion interrompue par la cible ou le réseau."

    if isinstance(exc, ConnectionError):
        return "Connexion réseau interrompue."

    return "Erreur réseau non détaillée (détails masqués)."
