"""V25.0 opt-in real Paramiko SSH transport; no Qt/legacy-route changes."""
from dataclasses import dataclass
from pathlib import Path
from guarded_ssh_adapter import GuardedSSHAdapter
from ssh_security import known_hosts_preflight, resolve_password

@dataclass(frozen=True)
class SSHSettings:
    hostname: str
    username: str
    port: int = 22
    timeout: float = 15.0
    known_hosts: str | None = None

    def validate(self):
        if not self.hostname.strip() or not self.username.strip():
            raise ValueError('hostname and username required')
        if not 1 <= self.port <= 65535 or self.timeout <= 0:
            raise ValueError('invalid SSH port or timeout')


def create_ssh_client(settings: SSHSettings, *, password=None, key_filename=None, client_factory=None, policy_factory=None, credential_ref=None, credential_provider=None):
    """Connect with strict host-key verification; caller owns returned client.

    Authentication secrets must be provided at runtime, not persisted in config.
    """
    settings.validate()
    if credential_ref is not None and password is not None:
        raise ValueError('choose password or credential_ref, not both')
    if credential_ref is not None:
        password = resolve_password(credential_ref, credential_provider)
    if client_factory is None:
        import paramiko
        client_factory = paramiko.SSHClient
    client = client_factory()
    try:
        verified_hosts = known_hosts_preflight(settings.known_hosts)
        if verified_hosts:
            client.load_host_keys(verified_hosts)
        else:
            client.load_system_host_keys()
        if policy_factory is None:
            import paramiko
            policy_factory = paramiko.RejectPolicy
        client.set_missing_host_key_policy(policy_factory())
        client.connect(hostname=settings.hostname, port=settings.port,
                       username=settings.username, password=password,
                       key_filename=key_filename, timeout=settings.timeout,
                       auth_timeout=settings.timeout, banner_timeout=settings.timeout,
                       look_for_keys=False, allow_agent=False)
        return client
    except BaseException:
        client.close()
        raise


def guarded_ssh_session(session_id, settings, *, password=None, key_filename=None, client_factory=None, policy_factory=None, credential_ref=None, credential_provider=None):
    """Return an opt-in guarded adapter; caller invokes connect/cancel/close."""
    return GuardedSSHAdapter(session_id,
        lambda: create_ssh_client(settings, password=password, key_filename=key_filename,
                                  client_factory=client_factory, policy_factory=policy_factory,
                                  credential_ref=credential_ref, credential_provider=credential_provider),
        timeout_seconds=settings.timeout)
