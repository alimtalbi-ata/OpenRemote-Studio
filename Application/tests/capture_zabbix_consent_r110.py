"""Capture the genuine Qt consent-revocation state; offline, no token or network."""
import os
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from qt_font_render_gate import configure_readable_offscreen_font
from zabbix_alerts_qt import ZabbixAlertsPanel

app = QApplication.instance() or QApplication([])
font = configure_readable_offscreen_font(app)
panel = ZabbixAlertsPanel([], token_provider=lambda: (_ for _ in ()).throw(
    AssertionError("R110 capture must never read a token")))
panel.resize(1260, 720)
panel.origin.setText("https://zabbix-a.example.invalid/zabbix")
panel.consent.setChecked(True)
assert panel.consent.isChecked()
panel.origin.setText("https://zabbix-b.example.invalid/zabbix")
assert not panel.consent.isChecked(), "origin edit must revoke consent"
assert panel.table.topLevelItemCount() == 0
assert "révoqué" in panel.status.text().casefold()
dest = Path("Binary/Qualification/qt-zabbix-r110-consent-revoked.png")
dest.parent.mkdir(parents=True, exist_ok=True)
if not panel.grab().save(str(dest), "PNG"):
    raise SystemExit("R110_ZABBIX_CONSENT_CAPTURE_FAILED")
if not dest.read_bytes().startswith(bytes((137, 80, 78, 71, 13, 10, 26, 10))):
    raise SystemExit("R110_ZABBIX_CONSENT_CAPTURE_INVALID")
panel.close()
print("R110_ZABBIX_CONSENT_REVOKED_CAPTURE_PASS", dest.as_posix(), dest.stat().st_size, "font=" + font)
