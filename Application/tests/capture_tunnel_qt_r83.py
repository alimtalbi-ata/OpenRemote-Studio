"""Capture an actual offscreen Qt render of the *offline* SSH tunnel panel.
Windows CI only. No network, credentials, hostnames or user data are loaded.
Author: Abdelhalim Talbi.
"""
import hashlib
import os
from pathlib import Path

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from ssh_tunnel_qt import SSHTunnelPanel


def main():
    app = QApplication.instance() or QApplication([])
    panel = SSHTunnelPanel()
    assert not panel.consent.isChecked(), 'offline default violated'
    assert panel._controller.poll().phase == 'idle', 'network was started'
    panel.resize(900, 740)
    panel.show()
    app.processEvents()
    output = Path('Binary/Qualification/qt-tunnel-r83-offline.png')
    output.parent.mkdir(parents=True, exist_ok=True)
    if not panel.grab().save(str(output), 'PNG'):
        raise RuntimeError('Qt screenshot capture failed')
    data = output.read_bytes()
    if len(data) < 4000 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('Invalid screenshot bytes')
    sha = hashlib.sha256(data).hexdigest()
    (output.parent / 'qt-tunnel-r83-offline.sha256').write_text(
        sha + '  ' + output.name + '\n', encoding='ascii')
    panel.close()
    print('R83_QT_REAL_RENDER_PASS: offscreen Windows Qt, offline, SHA256=' + sha)


if __name__ == '__main__':
    main()
