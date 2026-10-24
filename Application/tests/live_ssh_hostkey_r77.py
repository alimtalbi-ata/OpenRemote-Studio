"""R77 live OpenSSH host-key acceptance, isolated CI fixture only.

The first untrusted key read below is allowed ONLY to bootstrap the disposable
OpenSSH CI container. In production, known_hosts must come from a trusted
out-of-band channel; never learn a remote key on first use.
Author: Abdelhalim Talbi.
"""
import os
import socket
import tempfile
from pathlib import Path

import paramiko
from ssh_transport import SSHSettings, create_ssh_client


def fixture_known_hosts(host, port, path):
    """Trust-on-first-use for the ephemeral, loopback-only CI server ONLY."""
    if host not in ('127.0.0.1', '::1'):
        raise ValueError('fixture must bind to loopback')
    with socket.create_connection((host, port), timeout=10) as sock:
        transport = paramiko.Transport(sock)
        try:
            transport.start_client(timeout=10)
            key = transport.get_remote_server_key()
        finally:
            transport.close()
    entry = f'[{host}]:{port}' if port != 22 else host
    known = paramiko.HostKeys()
    known.add(entry, key.get_name(), key)
    known.save(str(path))
    return path


def run():
    host = os.environ.get('SFTP_TEST_HOST', '127.0.0.1')
    port = int(os.environ.get('SFTP_TEST_PORT', '2222'))
    password = os.environ.get('SFTP_TEST_PASSWORD', 'testpassword')  # Disposable CI fixture.
    with tempfile.TemporaryDirectory(prefix='ors-r77-hostkey-') as folder:
        root = Path(folder)
        pinned = fixture_known_hosts(host, port, root / 'pinned_hosts')
        settings = SSHSettings(host, 'tester', port=port, timeout=10, known_hosts=str(pinned))
        client = create_ssh_client(settings, password=password)
        try:
            with client.open_sftp() as sftp:
                assert sftp.listdir('/upload') is not None
        finally:
            client.close()

        # Known_hosts exists but has no entry for the actual endpoint.
        missing = root / 'unrelated_hosts'
        known = paramiko.HostKeys()
        known.add('unrelated.example', 'ssh-rsa', paramiko.RSAKey.generate(2048))
        known.save(str(missing))
        try:
            unexpected = create_ssh_client(SSHSettings(host, 'tester', port=port,
                timeout=10, known_hosts=str(missing)), password=password)
        except paramiko.SSHException:
            pass
        else:
            unexpected.close()
            raise AssertionError('unknown SSH host key was accepted')

        # A deliberately wrong key for the same endpoint must also fail closed.
        wrong = root / 'wrong_hosts'
        known = paramiko.HostKeys()
        entry = f'[{host}]:{port}' if port != 22 else host
        known.add(entry, 'ssh-rsa', paramiko.RSAKey.generate(2048))
        known.save(str(wrong))
        try:
            unexpected = create_ssh_client(SSHSettings(host, 'tester', port=port,
                timeout=10, known_hosts=str(wrong)), password=password)
        except paramiko.SSHException:
            pass
        else:
            unexpected.close()
            raise AssertionError('incorrect SSH host key was accepted')
    print('LIVE_OPENSSH_R77_PASS: pinned key login + SFTP, unknown/wrong keys rejected')


if __name__ == '__main__':
    run()
