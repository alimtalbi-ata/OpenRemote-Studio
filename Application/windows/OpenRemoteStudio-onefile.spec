# -*- mode: python ; coding: utf-8 -*-
# Optional compact, self-extracting single executable. Requires Windows for build.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules
root = Path(SPECPATH).resolve().parent
hidden = (collect_submodules('paramiko') + collect_submodules('winrm')
          + collect_submodules('spnego'))
a = Analysis([str(root / 'qt_app.py')], pathex=[str(root)], binaries=[], datas=[(str(root.parent / 'VERSION.txt'), '.')],
             hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['tkinter', 'unittest', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='OpenRemoteStudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
