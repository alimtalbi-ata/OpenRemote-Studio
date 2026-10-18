"""Exercise the real Qt entrypoint with isolated local settings and no connections."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 unavailable')
class QtRuntimeStartupTests(unittest.TestCase):
    def test_main_window_starts_and_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', APPDATA=tmp,
                       LOCALAPPDATA=tmp, XDG_CONFIG_HOME=tmp, XDG_CACHE_HOME=tmp)
            result = subprocess.run(
                [sys.executable, '-B', 'qt_app.py', '--smoke-gui'],
                cwd=Path(__file__).resolve().parents[1], env=env,
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('OPENREMOTE_GUI_SMOKE_PASS', result.stdout)
