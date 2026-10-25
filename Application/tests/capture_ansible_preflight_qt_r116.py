"""Capture the genuine R116 Qt panel in offline mode; never contacts Ansible/SSH."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "Application"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from PySide6.QtWidgets import QApplication
from ansible_preflight_qt import AnsiblePreflightPanel


def main():
    app = QApplication.instance() or QApplication([])
    pane = AnsiblePreflightPanel(executable_lookup=lambda _name: None)
    pane.resize(1180, 720)
    pane.show()
    app.processEvents()
    target = ROOT / "Binary" / "Qualification" / "ansible-preflight-r116.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not pane.grab().save(str(target), "PNG"):
        raise SystemExit("R116 offline Qt screenshot could not be saved")
    if target.stat().st_size < 1024:
        raise SystemExit("R116 offline Qt screenshot is unexpectedly small")
    pane.close()
    print("R116_QT_OFFLINE_SCREENSHOT_PASS: actual Qt rendering; no network and no Ansible CLI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
