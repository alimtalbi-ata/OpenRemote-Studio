"""R90: real Qt offscreen clicks against disposable loopback OpenSSH.

No screenshot is saved: form fields contain fixture private-key paths.
No production server, automatic host-key acceptance or credential logging.
Author: Abdelhalim Talbi.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import socket
import tempfile
import time
from pathlib import Path

import paramiko
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from live_ssh_hostkey_r77 import fixture_known_hosts
from live_ssh_tunnel_r78 import free_port
from ssh_tunnel_qt import SSHTunnelPanel


def until(app, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(.025)
    return False


def click(widget):
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton)


def run():
    host = os.environ.get('SFTP_TEST_HOST')
    port = int(os.environ.get('SFTP_TEST_PORT', '0'))
    key = Path(os.environ['R82_SSH_KEY_PATH'])
    if host != '127.0.0.1' or port != 2222 or not key.is_file():
        raise RuntimeError('R90 requires disposable loopback OpenSSH fixture')

    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='ors-r90-') as tmp:
        root = Path(tmp)
        trusted = fixture_known_hosts(host, port, root / 'trusted_hosts')
        wrong = root / 'wrong_hosts'
        keys = paramiko.HostKeys()
        keys.add(f'[{host}]:{port}', 'ssh-rsa', paramiko.RSAKey.generate(2048))
        keys.save(str(wrong))
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
        panel.known_hosts.setText(str(wrong))
        panel.keepalive_seconds.setText('15')
        try:
            click(panel.consent)
            assert panel.consent.isChecked()
            click(panel.start_button)
            assert until(app, lambda: panel._controller.poll().phase == 'failed'), 'wrong pin timeout'
            panel._refresh()
            assert 'known_hosts' in panel.status.text(), 'host-key failure not actionable'
            assert panel.retry_button.isEnabled(), 'retry missing after cleanup'
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', local_port))

            click(panel.retry_button)
            assert not panel.consent.isChecked(), 'retry reused old consent'
            panel.known_hosts.setText(str(trusted))
            click(panel.start_button)
            assert not panel._controller.poll().phase == 'active', 'connected without fresh consent'
            click(panel.consent)
            click(panel.start_button)
            assert until(app, lambda: panel._controller.poll().phase in ('active', 'failed'))
            assert panel._controller.poll().phase == 'active', 'retry failed'
            with socket.create_connection(('127.0.0.1', local_port), timeout=5) as peer:
                peer.settimeout(5)
                assert peer.recv(64).startswith(b'SSH-2.0-'), 'real forwarding failed'

            # Programmatic edits must revoke even when Qt marks the field read-only.
            panel.target_port.setText('2222')
            assert until(app, panel.is_shutdown_complete), 'revocation did not drain'
            assert not panel.consent.isChecked(), 'stale consent remained'
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', local_port))
        finally:
            panel.request_close()
            assert until(app, panel.is_shutdown_complete), 'final cleanup incomplete'
            panel._timer.stop()
            panel.close()

    print('LIVE_OPENSSH_QT_R90_PASS: wrong host key rejected; fresh consent required; '
          'real forwarding and live-edit revocation verified')


if __name__ == '__main__':
    run()
