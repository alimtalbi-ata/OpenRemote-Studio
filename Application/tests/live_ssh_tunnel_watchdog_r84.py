"""R84 live OpenSSH fixture: detect lost Paramiko transport and revoke listener.
This closes the client-side SSH transport only; no production or server changes.
Author: Abdelhalim Talbi.
"""
import os
import socket
import tempfile
from pathlib import Path
from live_ssh_hostkey_r77 import fixture_known_hosts
from live_ssh_tunnel_controller_r82 import wait_for
from live_ssh_tunnel_r78 import free_port
from ssh_transport import SSHSettings, create_ssh_client
from tunnel_controller import TunnelController


def run():
    host = os.environ.get('SFTP_TEST_HOST', '127.0.0.1')
    port = int(os.environ.get('SFTP_TEST_PORT', '2222'))
    key = os.environ['R82_SSH_KEY_PATH']
    if host != '127.0.0.1' or not Path(key).is_file():
        raise RuntimeError('R84 requires disposable loopback OpenSSH fixture')
    with tempfile.TemporaryDirectory(prefix='ors-r84-') as directory:
        trusted = fixture_known_hosts(host, port, Path(directory) / 'known_hosts')
        settings = SSHSettings(host, 'tester', port=port, timeout=10,
                               known_hosts=str(trusted))
        clients = []
        def connector(config, **kwargs):
            client = create_ssh_client(config, **kwargs)
            clients.append(client)
            return client
        local = free_port()
        controller = TunnelController(connector=connector)
        controller.start(settings, key_filename=key, local_port=local,
                         target_host='127.0.0.1', target_port=22)
        assert wait_for(lambda: controller.poll().phase in ('active', 'failed'))
        assert controller.poll().phase == 'active', 'real SSH authentication failed'
        with socket.create_connection(('127.0.0.1', local), timeout=5) as peer:
            peer.settimeout(5)
            assert peer.recv(64).startswith(b'SSH-2.0-'), 'forwarding failed'
            clients[0].get_transport().close()  # Simulated abrupt SSH link loss.
            # Do not call poll(): the watchdog must revoke forwarding headlessly.
            assert wait_for(lambda: controller._scope.cancelled), 'headless watchdog did not revoke'
            assert wait_for(lambda: controller.poll().phase == 'disconnected'), 'disconnect not drained'
            assert controller.is_shutdown_complete()
        with socket.socket() as probe:
            # Match the listener's SO_REUSEADDR: accepted TCP peers may leave TIME_WAIT.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', local))
    print('LIVE_OPENSSH_R84_PASS: real key-only tunnel, transport loss, listener revoked')


if __name__ == '__main__':
    run()
