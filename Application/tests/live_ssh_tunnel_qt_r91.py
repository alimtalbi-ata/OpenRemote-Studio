"""R91: real OpenSSH/Qt revocation after explicit consent withdrawal.

Runs only against a disposable loopback OpenSSH fixture in GitHub Actions.
No screenshots or sensitive endpoint/key paths are persisted.
Author: Abdelhalim Talbi.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import socket
import tempfile
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication
from ssh_tunnel_qt import SSHTunnelPanel
from live_ssh_hostkey_r77 import fixture_known_hosts
from live_ssh_tunnel_r78 import free_port
from live_ssh_tunnel_qt_r90 import click, until


def assert_port_released(port):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))


def run():
    host = os.environ.get('SFTP_TEST_HOST')
    port = int(os.environ.get('SFTP_TEST_PORT', '0'))
    key = Path(os.environ.get('R82_SSH_KEY_PATH', ''))
    if host != '127.0.0.1' or port != 2222 or not key.is_file():
        raise RuntimeError('R91 requires disposable loopback OpenSSH fixture')

    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='ors-r91-') as tmp:
        known_hosts = fixture_known_hosts(host, port, Path(tmp) / 'known_hosts')
        local_port = free_port()
        panel = SSHTunnelPanel()
        panel.show()
        panel.host.setText(host)
        panel.user.setText('tester')
        panel.ssh_port.setText(str(port))
        panel.local_port.setText(str(local_port))
        panel.target_host.setText('127.0.0.1')
        panel.target_port.setText('22')
        panel.key_file.setText(str(key))
        panel.known_hosts.setText(str(known_hosts))
        try:
            click(panel.consent)
            click(panel.start_button)
            assert until(app, lambda: panel._controller.poll().phase in ('active', 'failed')), 'SSH startup timeout'
            assert panel._controller.poll().phase == 'active', 'SSH authentication or pinning failed'
            with socket.create_connection(('127.0.0.1', local_port), timeout=5) as peer:
                peer.settimeout(5)
                assert peer.recv(64).startswith(b'SSH-2.0-'), 'forwarding unavailable'

            # Qt permits programmatic setChecked() even on disabled controls.
            # Withdrawing approval MUST close an already active real tunnel.
            panel.consent.setChecked(False)
            assert until(app, panel.is_shutdown_complete), 'consent withdrawal did not drain'
            assert not panel._consent_guard.approved, 'approval survived withdrawal'
            assert_port_released(local_port)

            panel.start_tunnel()  # no new network operation without fresh approval
            assert 'autorisation' in panel.status.text(), 'missing fail-closed status'
            assert panel.retry_button.isEnabled(), 'manual retry unavailable'
            click(panel.retry_button)
            assert not panel.consent.isChecked(), 'retry silently restored consent'
            click(panel.start_button)
            assert panel._controller.poll().phase == 'idle', 'retry connected without approval'
            click(panel.consent)
            click(panel.start_button)
            assert until(app, lambda: panel._controller.poll().phase in ('active', 'failed')), 'retry timeout'
            assert panel._controller.poll().phase == 'active', 'manual reapproval failed'
        finally:
            panel.request_close()
            assert until(app, panel.is_shutdown_complete), 'final cleanup incomplete'
            panel._timer.stop()
            panel.close()
            assert_port_released(local_port)

    print('LIVE_OPENSSH_QT_R91_PASS: consent withdrawal revoked real listener; '
          'fresh approval required for manual retry')


if __name__ == '__main__':
    run()
