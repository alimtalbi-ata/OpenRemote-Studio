"""V25.1 SSH credential resolution and host-key preflight, opt-in."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CredentialRef:
    """Opaque credential identifier; no password is serialized."""
    identifier: str
    def __post_init__(self):
        if not self.identifier or not self.identifier.strip():
            raise ValueError('credential reference is required')


class CredentialUnavailable(RuntimeError):
    pass


def resolve_password(ref: CredentialRef, provider):
    """Resolve only at connection time using an injected credential provider."""
    if provider is None:
        raise CredentialUnavailable('credential provider not configured')
    value = provider(ref.identifier)
    if not isinstance(value, str) or not value:
        raise CredentialUnavailable('credential unavailable')
    return value


def known_hosts_preflight(path: str | None):
    """Check explicit host-key file before creating a client; do not alter it."""
    if path is None:
        return None
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError('known_hosts file missing')
    if p.stat().st_size == 0:
        raise ValueError('known_hosts file is empty')
    return str(p)
