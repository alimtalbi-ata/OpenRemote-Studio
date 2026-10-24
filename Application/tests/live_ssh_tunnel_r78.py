"""R78 live SSH direct-tcpip acceptance against disposable loopback OpenSSH.

Only the CI fixture may bootstrap its known_hosts with TOFU. The actual
application connects using pinned known_hosts + RejectPolicy. No production
server, credentials, or target network is accessed. Author: Abdelhalim Talbi.
"""
import os
import socket
import tempfile
import time
from pathlib import Path

from live_ssh_hostkey_r77 import fixture_known_hosts
from remote_tools import Tunnel
from ssh_transport import SSHSettings, create_ssh_client


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def wait_for(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.05)
    return predicate()


def run():
    host = os.environ.get('SFTP_TEST_HOST', '127.0.0.1')
    port = int(os.environ.get('SFTP_TEST_PORT', '2222'))
    if host != '127.0.0.1':
        raise RuntimeError('R78 live test requires IPv4 loopback fixture')
    with tempfile.TemporaryDirectory(prefix='ors-r78-tunnel-') as folder:
        pinned = fixture_known_hosts(host, port, Path(folder) / 'known_hosts')
        client = create_ssh_client(SSHSettings(host, 'tester', port=port, timeout=10,
                                               known_hosts=str(pinned)),
                                   password=os.environ.get('SFTP_TEST_PASSWORD', 'testpassword'))
        tunnel = None
        try:
            listen_port = free_port()
            # Target is sshd inside the SAME disposable container. No LAN access.
            tunnel = Tunnel(client, '127.0.0.1', listen_port, '127.0.0.1', 22,
                            max_connections=1)
            tunnel.start()
            with socket.create_connection(('127.0.0.1', listen_port), timeout=5) as peer:
                peer.settimeout(5)
                banner = b''
                while not banner.endswith(b'\n') and len(banner) < 256:
                    chunk = peer.recv(1)
                    if not chunk:
                        break
                    banner += chunk
                assert banner.startswith(b'SSH-2.0-'), 'SSH banner did not traverse tunnel'
                assert wait_for(lambda: tunnel.active_connections == 1)
                tunnel.close()  # Must revoke the ALREADY OPEN connection.
                assert wait_for(lambda: tunnel.active_connections == 0)
                try:
                    assert peer.recv(1) == b'', 'peer remained connected after revocation'
                except (ConnectionResetError, BrokenPipeError):
                    pass
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(('127.0.0.1', listen_port))
            print('LIVE_OPENSSH_R78_PASS: pinned host-key, real direct-tcpip, active revoke, port release')
        finally:
            if tunnel is not None:
                tunnel.close()
            client.close()


if __name__ == '__main__':
    run()
