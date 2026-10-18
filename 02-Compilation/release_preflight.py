"""V27.0 release preflight: fail closed on missing Qt or missing mandatory files."""
import importlib.util
import sys
from pathlib import Path

def check(root, qt_available=None):
    root = Path(root)
    mandatory = [root / "VERSION.txt", root / "Application" / "qt_app.py", root / "Application" / "ssh_qt_bridge.py", root / "02-Compilation" / "qualify_qt.py"]
    absent = [str(p.relative_to(root)) for p in mandatory if not p.is_file()]
    if absent:
        return 2, "BLOCK: missing mandatory files: " + ", ".join(absent)
    if qt_available is None:
        qt_available = importlib.util.find_spec("PySide6") is not None
    if not qt_available:
        return 3, "BLOCK: PySide6 absent; Qt tests cannot be certified"
    return 0, "READY: mandatory files and PySide6 present; run qualify_qt.py and Windows E2E"

if __name__ == "__main__":
    code, message = check(Path(__file__).resolve().parents[1])
    print(message)
    sys.exit(code)
