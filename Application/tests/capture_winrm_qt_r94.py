"""R94 genuine Qt offscreen screenshot of offline WinRM panel; no network or secrets.

Capture is from the Windows CI runner, not a human-operated Windows desktop.
Author: Abdelhalim Talbi.
"""
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from winrm_inventory_qt import WinRMInventoryPanel

app = QApplication.instance() or QApplication([])
panel = WinRMInventoryPanel()
panel.resize(900, 560)
panel.show()
app.processEvents()
assert not panel.consent.isChecked()
assert panel.table.topLevelItemCount() == 0
assert 'Hors ligne' in panel.status.text()
destination = Path('Binary/Qualification/qt-winrm-r94-offline.png')
destination.parent.mkdir(parents=True, exist_ok=True)
if not panel.grab().save(str(destination), 'PNG'):
    raise SystemExit('R94_QT_CAPTURE_FAILED')
if not destination.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
    raise SystemExit('R94_QT_CAPTURE_INVALID')
panel.close()
print('R94_QT_OFFLINE_CAPTURE_PASS', destination.as_posix(), destination.stat().st_size)
