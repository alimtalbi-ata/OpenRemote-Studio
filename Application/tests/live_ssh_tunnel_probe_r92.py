"""R92 real OpenSSH response probe and paused disposable sshd.
Not a WAN blackhole test. Requires GitHub Actions loopback Docker fixture.
Author: Abdelhalim Talbi.
"""
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

from live_ssh_hostkey_r77 import fixture_known_hosts
from live_ssh_tunnel_r78 import free_port
from ssh_transport import SSHSettings
from tunnel_controller import TunnelController


def until(predicate, seconds=12):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.05)
    return predicate()


def run():
    host = os.environ.get('SFTP_TEST_HOST')
    port = int(os.environ.get('SFTP_TEST_PORT', '0'))
    key = Path(os.environ.get('R82_SSH_KEY_PATH', ''))
    if (os.environ.get('GITHUB_ACTIONS') != 'true' or host != '127.0.0.1'
            or port != 2222 or not key.is_file()):
        raise RuntimeError('R92 requires disposable GitHub Actions OpenSSH fixture')
    # The fixture is owned by this workflow. Never pause a user-supplied host.
    fixture = subprocess.run(['docker', 'inspect', '-f', '{{.Name}}', 'openremote-sftp'],
                             check=True, capture_output=True, text=True)
    if fixture.stdout.strip() != '/openremote-sftp':
        raise RuntimeError('unexpected disposable container')

    with tempfile.TemporaryDirectory(prefix='ors-r92-') as tmp:
        trusted = fixture_known_hosts(host, port, Path(tmp) / 'known_hosts')
        local_port = free_port()
        controller = TunnelController()
        controller.start(SSHSettings(host, 'tester', port=port, timeout=10,
                                     known_hosts=str(trusted)),
                         key_filename=str(key), local_port=local_port,
                         target_host='127.0.0.1', target_port=22,
                         probe_interval_seconds=1, probe_timeout_seconds=2)
        paused = False
        try:
            assert until(lambda: controller.poll().phase in ('active', 'failed')), 'startup timed out'
            assert controller.poll().phase == 'active', 'real pinned SSH unavailable'
            with socket.create_connection(('127.0.0.1', local_port), timeout=5) as peer:
                peer.settimeout(5)
                assert peer.recv(64).startswith(b'SSH-2.0-'), 'real forwarding failed'
            # First verify that OpenSSH replies (including REQUEST_FAILURE).
            time.sleep(2.5)
            assert controller.poll().phase == 'active', 'normal OpenSSH probe falsely revoked'

            # Pausing this isolated sshd starves SSH global-request replies while
            # the TCP connection may still appear established to the client.
            subprocess.run(['docker', 'pause', 'openremote-sftp'], check=True,
                           capture_output=True)
            paused = True
            # Deliberately no Qt event loop or controller.poll() before cancellation.
            assert until(lambda: controller._scope.cancelled, 8), 'unanswered SSH probe not revoked'
            assert until(controller.is_shutdown_complete, 8), 'SSH listener not drained'
            assert controller.poll().phase == 'disconnected', 'expected sanitized disconnect'
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', local_port))
        finally:
            if paused:
                subprocess.run(['docker', 'unpause', 'openremote-sftp'], check=True,
                               capture_output=True)
            controller.stop()
    print('LIVE_OPENSSH_R92_PASS: normal SSH response; paused disposable sshd; '
          'unanswered probe revoked loopback listener')


if __name__ == '__main__':
    run()
