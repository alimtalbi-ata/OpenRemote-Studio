"""R80: real OpenSSH host-key rotation in a disposable CI container ONLY.

The trusted key comes from the local Docker fixture, NOT from the network.
Never auto-accept a changed host key or apply this procedure to production.
Author: Abdelhalim Talbi.
"""
import base64
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import paramiko
from ssh_transport import SSHSettings, create_ssh_client


def docker(*args):
    return subprocess.run(['docker', *args], check=True, capture_output=True,
                          text=True, timeout=30).stdout


def trusted_public_key(container_path):
    """Read a fixture public key out-of-band via Docker, never SSH scanning."""
    fields = docker('exec', 'openremote-sftp', 'cat', container_path).split()
    if len(fields) < 2 or fields[0] != 'ssh-ed25519':
        raise AssertionError('fixture requires an ed25519 public host key')
    raw = base64.b64decode(fields[1], validate=True)
    return paramiko.PKey.from_type_string(fields[0], raw)


def pin(host, port, key, path):
    known = paramiko.HostKeys()
    entry = f'[{host}]:{port}' if port != 22 else host
    known.add(entry, key.get_name(), key)
    known.save(str(path))
    return path


def connect(host, port, known_hosts):
    return create_ssh_client(SSHSettings(host, 'tester', port=port, timeout=8,
                                        known_hosts=str(known_hosts)),
                             password=os.environ.get('SFTP_TEST_PASSWORD', 'testpassword'))


def wait_for_fixture(host, port):
    for _ in range(40):
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(.25)
    raise TimeoutError('disposable OpenSSH fixture did not restart')


def run():
    host = os.environ.get('SFTP_TEST_HOST', '127.0.0.1')
    port = int(os.environ.get('SFTP_TEST_PORT', '2222'))
    if (os.environ.get('GITHUB_ACTIONS') != 'true' or host != '127.0.0.1'
            or port != 2222):
        raise RuntimeError('R80 rotation is restricted to disposable GitHub CI loopback')
    with tempfile.TemporaryDirectory(prefix='ors-r80-rotation-') as folder:
        root = Path(folder)
        old_key = trusted_public_key('/etc/ssh/ssh_host_ed25519_key.pub')
        old_pin = pin(host, port, old_key, root / 'old_known_hosts')
        client = connect(host, port, old_pin)
        try:
            with client.open_sftp() as sftp:
                assert isinstance(sftp.listdir('/upload'), list)
        finally:
            client.close()

        # Generate the new host key in the CI container, inspect only its
        # PUBLIC key over Docker's local control plane (out-of-band fixture).
        docker('exec', '-u', 'root', 'openremote-sftp', 'ssh-keygen', '-q',
               '-t', 'ed25519', '-N', '', '-f', '/tmp/ors-r80-new-hostkey')
        new_key = trusted_public_key('/tmp/ors-r80-new-hostkey.pub')
        if old_key.asbytes() == new_key.asbytes():
            raise AssertionError('fixture host key did not change')
        new_pin = pin(host, port, new_key, root / 'new_known_hosts')
        docker('exec', '-u', 'root', 'openremote-sftp', 'sh', '-ec',
               'cp /tmp/ors-r80-new-hostkey /etc/ssh/ssh_host_ed25519_key; '
               'cp /tmp/ors-r80-new-hostkey.pub /etc/ssh/ssh_host_ed25519_key.pub; '
               'chmod 600 /etc/ssh/ssh_host_ed25519_key; /usr/sbin/sshd -t')
        docker('restart', 'openremote-sftp')
        wait_for_fixture(host, port)

        # Old pin MUST reject changed host key before any SFTP operation.
        try:
            unexpected = connect(host, port, old_pin)
        except paramiko.BadHostKeyException:
            pass
        else:
            unexpected.close()
            raise AssertionError('old pinned SSH key accepted after rotation')

        # Explicit trusted replacement pin permits a NEW connection.
        client = connect(host, port, new_pin)
        try:
            with client.open_sftp() as sftp:
                assert isinstance(sftp.listdir('/upload'), list)
        finally:
            client.close()
        print('LIVE_OPENSSH_R80_PASS: trusted fixture rotation, old pin rejected, new pin accepted')


if __name__ == '__main__':
    run()
