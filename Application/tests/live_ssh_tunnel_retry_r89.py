"""R89: real, disposable OpenSSH failure guidance and explicit manual retry.

No production host or credential is accessed. Only 127.0.0.1 Docker fixture.
Author: Abdelhalim Talbi.
"""
import os
import socket
import subprocess
import tempfile
from pathlib import Path

import paramiko

from live_ssh_hostkey_r77 import fixture_known_hosts
from live_ssh_tunnel_controller_r82 import wait_for
from live_ssh_tunnel_r78 import free_port
from ssh_transport import SSHSettings
from tunnel_controller import TunnelController


def _start(host, port, key, known_hosts, local_port):
    controller = TunnelController()
    controller.start(
        SSHSettings(host, 'tester', port=port, timeout=10,
                    known_hosts=str(known_hosts)),
        key_filename=str(key), local_port=local_port,
        target_host='127.0.0.1', target_port=22, keepalive_seconds=15)
    return controller


def run():
    host = os.environ.get('SFTP_TEST_HOST', '127.0.0.1')
    port = int(os.environ.get('SFTP_TEST_PORT', '2222'))
    key = Path(os.environ['R82_SSH_KEY_PATH'])
    if host != '127.0.0.1' or port != 2222 or not key.is_file():
        raise RuntimeError('R89 requires the disposable loopback OpenSSH fixture')

    with tempfile.TemporaryDirectory(prefix='ors-r89-') as temp:
        root = Path(temp)
        trusted = fixture_known_hosts(host, port, root / 'trusted_hosts')
        wrong = root / 'wrong_hosts'
        hostkeys = paramiko.HostKeys()
        hostkeys.add(f'[{host}]:{port}', 'ssh-rsa', paramiko.RSAKey.generate(2048))
        hostkeys.save(str(wrong))

        local_port = free_port()
        rejected = _start(host, port, key, wrong, local_port)
        assert wait_for(rejected.is_shutdown_complete), 'wrong host-key attempt timed out'
        rejected_state = rejected.poll()
        assert rejected_state.phase == 'failed', 'wrong host key accepted'
        assert rejected_state.failure_code == 'host_key', 'wrong host key not classified'
        assert str(key) not in str(rejected_state), 'private key path leaked'
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', local_port))  # No listener on failed pin.

        # Explicit correction of trust via an out-of-band lab fixture, never TOFU.
        # One-shot controller must be replaced. No automatic retry.
        accepted = _start(host, port, key, trusted, local_port)
        try:
            assert wait_for(lambda: accepted.poll().phase in ('active', 'failed'))
            assert accepted.poll().phase == 'active', 'manual retry failed'
            with socket.create_connection(('127.0.0.1', local_port), timeout=5) as peer:
                peer.settimeout(5)
                assert peer.recv(64).startswith(b'SSH-2.0-'), 'forwarding failed'
        finally:
            accepted.stop()
        assert wait_for(accepted.is_shutdown_complete), 'retry did not drain'

        # Paramiko tries Ed25519 last. A rejected Ed25519 key preserves the
        # AuthenticationException instead of overwriting it with a parser
        # SSHException from trying other key formats after a rejected RSA key.
        unauthorized = root / 'unauthorized_ed25519_key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                        '-f', str(unauthorized)], check=True,
                       capture_output=True)
        denied = _start(host, port, unauthorized, trusted, free_port())
        assert wait_for(denied.is_shutdown_complete), 'auth failure timed out'
        denied_state = denied.poll()
        assert denied_state.phase == 'failed', 'unauthorized key accepted'
        assert denied_state.failure_code == 'authentication', 'auth failure not classified'
        assert str(unauthorized) not in str(denied_state), 'credential path leaked'

    print('LIVE_OPENSSH_R89_PASS: wrong host-key denied; explicit retry works; '
          'unauthorized key classified without exposing details')


if __name__ == '__main__':
    run()
