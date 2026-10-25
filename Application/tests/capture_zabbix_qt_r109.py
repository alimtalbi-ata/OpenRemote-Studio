"""Capture the real R109 Zabbix Qt panel in offline mode; no token or network."""
import os
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from qt_font_render_gate import configure_readable_offscreen_font
from zabbix_alerts_qt import ZabbixAlertsPanel

app = QApplication.instance() or QApplication([])
font = configure_readable_offscreen_font(app)
panel = ZabbixAlertsPanel([
    {"name": "EXEMPLE-SRV-01", "protocol": "SSH", "host": "srv01.example.invalid"},
])
panel.resize(1260, 720)
panel.origin.setText("https://zabbix.example.invalid/zabbix")
panel.show()
app.processEvents()
assert not panel.consent.isChecked()
assert panel.table.topLevelItemCount() == 0
assert "Hors ligne" in panel.status.text()
dest = Path("Binary/Qualification/qt-zabbix-r109-offline.png")
dest.parent.mkdir(parents=True, exist_ok=True)
if not panel.grab().save(str(dest), "PNG"):
    raise SystemExit("R109_ZABBIX_QT_CAPTURE_FAILED")
if not dest.read_bytes().startswith(bytes((137, 80, 78, 71, 13, 10, 26, 10))):
    raise SystemExit("R109_ZABBIX_QT_CAPTURE_INVALID")
panel.close()
print("R109_ZABBIX_QT_OFFLINE_CAPTURE_PASS", dest.as_posix(), dest.stat().st_size, "font=" + font)
