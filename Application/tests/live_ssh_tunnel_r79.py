"""R79 disposable OpenSSH acceptance: concurrent close cannot return early.

This is a CI-only loopback fixture, not a production or Windows operator test.
Author: Abdelhalim Talbi.
"""
import os
import socket
import tempfile
import threading
from pathlib import Path

from live_ssh_hostkey_r77 import fixture_known_hosts
from live_ssh_tunnel_r78 import free_port
from remote_tools import Tunnel
from ssh_transport import SSHSettings, create_ssh_client


def run():
    host = os.environ.get('SFTP_TEST_HOST', '127.0.0.1')
    port = int(os.environ.get('SFTP_TEST_PORT', '2222'))
    if host != '127.0.0.1':
        raise RuntimeError('R79 requires disposable IPv4 loopback fixture')
    with tempfile.TemporaryDirectory(prefix='ors-r79-') as folder:
        pinned = fixture_known_hosts(host, port, Path(folder) / 'known_hosts')
        client = create_ssh_client(SSHSettings(host, 'tester', port=port, timeout=10,
                                               known_hosts=str(pinned)),
                                   password=os.environ.get('SFTP_TEST_PASSWORD', 'testpassword'))
        tunnel = None
        try:
            listen_port = free_port()
            tunnel = Tunnel(client, '127.0.0.1', listen_port, '127.0.0.1', 22)
            tunnel.start()
            with socket.create_connection(('127.0.0.1', listen_port), timeout=5) as peer:
                peer.settimeout(5)
                banner = peer.recv(64)
                assert banner.startswith(b'SSH-2.0-'), 'real SSH forwarding unavailable'
                entered, release = threading.Event(), threading.Event()
                first_done, second_done = threading.Event(), threading.Event()
                original_shutdown = tunnel.server.shutdown
                failures = []

                def delayed_shutdown():
                    entered.set()
                    if not release.wait(5):
                        raise TimeoutError('R79 fixture teardown barrier timeout')
                    original_shutdown()

                def closer(done):
                    try:
                        tunnel.close()
                    except Exception as exc:
                        failures.append(type(exc).__name__)
                    finally:
                        done.set()

                tunnel.server.shutdown = delayed_shutdown
                first = threading.Thread(target=closer, args=(first_done,), daemon=True)
                second = threading.Thread(target=closer, args=(second_done,), daemon=True)
                try:
                    first.start()
                    assert entered.wait(3), 'first close did not enter shutdown'
                    second.start()
                    assert not second_done.wait(.2), 'second close returned before teardown'
                finally:
                    release.set()
                    first.join(5)
                    second.join(5)
                assert first_done.is_set() and second_done.is_set() and not failures
                assert tunnel.active_connections == 0, 'real SSH channel not revoked'
                try:
                    assert peer.recv(1) == b'', 'real peer remained connected'
                except (ConnectionResetError, BrokenPipeError):
                    pass
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(('127.0.0.1', listen_port))
            print('LIVE_OPENSSH_R79_PASS: real pinned forwarding, concurrent close barrier, port release')
        finally:
            if tunnel is not None:
                tunnel.close()
            client.close()


if __name__ == '__main__':
    run()
