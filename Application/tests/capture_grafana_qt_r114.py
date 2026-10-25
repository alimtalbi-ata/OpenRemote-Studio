"""Capture the real R114 Grafana Qt panel offline; no token or network request.

This PNG documents only the UI's offline/consent-disabled state, not live Grafana.
Author: Abdelhalim Talbi.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from qt_font_render_gate import configure_readable_offscreen_font
from grafana_dashboard_qt import GrafanaDashboardsPanel

app = QApplication.instance() or QApplication([])
font = configure_readable_offscreen_font(app)
panel = GrafanaDashboardsPanel()
panel.resize(1260, 720)
panel.origin.setText("https://grafana.example.invalid")
panel.query.setText("capacity")
panel.show()
app.processEvents()

assert not panel.consent.isChecked(), "R114 capture must remain offline"
assert panel.table.topLevelItemCount() == 0, "No live or synthetic rows may be shown"
assert "Hors ligne" in panel.status.text(), "Offline status must be visible"

dest = Path("Binary/Qualification/qt-grafana-r114-offline.png")
dest.parent.mkdir(parents=True, exist_ok=True)
if not panel.grab().save(str(dest), "PNG"):
    raise SystemExit("R114_GRAFANA_QT_CAPTURE_FAILED")
if not dest.read_bytes().startswith(bytes((137, 80, 78, 71, 13, 10, 26, 10))):
    raise SystemExit("R114_GRAFANA_QT_CAPTURE_INVALID")
if dest.stat().st_size < 128:
    raise SystemExit("R114_GRAFANA_QT_CAPTURE_TOO_SMALL")

panel.close()
app.processEvents()
print("R114_GRAFANA_QT_OFFLINE_CAPTURE_PASS", dest.as_posix(), dest.stat().st_size, "font=" + font)
