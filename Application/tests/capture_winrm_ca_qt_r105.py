"""R105 genuine Qt offscreen screenshot: offline only, no server evidence."""
import os
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from winrm_inventory_qt import WinRMInventoryPanel
from qt_font_render_gate import configure_readable_offscreen_font
app=QApplication.instance() or QApplication([])
family=configure_readable_offscreen_font(app)
p=WinRMInventoryPanel();p.resize(980,640)
p.origin.setText('https://serveur.exemple.invalid:5986')
p.username.setText('lecteur-exemple')
p.show();app.processEvents()
assert p.ca_bundle.isVisible() and not p.consent.isChecked()
assert p.table.topLevelItemCount()==0 and 'Hors ligne' in p.status.text()
dest=Path('Binary/Qualification/qt-winrm-ca-r105-offline.png')
dest.parent.mkdir(parents=True,exist_ok=True)
if not p.grab().save(str(dest),'PNG'):raise SystemExit('R105_CAPTURE_FAILED')
if not dest.read_bytes().startswith(bytes((137,80,78,71,13,10,26,10))):raise SystemExit('R105_CAPTURE_INVALID')
p.close()
print('R105_QT_OFFLINE_CAPTURE_PASS',dest.as_posix(),dest.stat().st_size,'font='+family)
