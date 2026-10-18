
"""Bounded, shell-free network diagnostic command construction.
Author: Abdelhalim Talbi.
"""
import ipaddress
import re
import socket
import sys

_ALLOWED = {"ping", "dns", "traceroute"}
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")

def safe_host(value):
    if not isinstance(value,str) or not value or value != value.strip():
        raise ValueError("Hôte invalide")
    if any(ord(c)<33 or ord(c)==127 for c in value):
        raise ValueError("Caractère de contrôle dans l'hôte")
    # Bracketed IPv6 is accepted for GUI fields, but never passed with brackets.
    raw=value[1:-1] if value.startswith("[") and value.endswith("]") else value
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        pass
    if not _HOST_RE.fullmatch(raw) or ".." in raw or raw.startswith("-") or raw.endswith("."):
        raise ValueError("Nom d'hôte invalide")
    return raw

def command_args(kind, host, windows=None):
    if kind not in _ALLOWED:
        raise ValueError("Diagnostic inconnu")
    host=safe_host(host)
    if windows is None:
        windows=sys.platform.startswith("win")
    if kind=="ping":
        return ["ping", "-n" if windows else "-c", "4", host]
    if kind=="dns":
        return ["nslookup", host]
    return ["tracert" if windows else "traceroute", host]
