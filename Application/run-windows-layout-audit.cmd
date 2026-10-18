@echo off
setlocal
cd /d "%~dp0"
python windows_layout_audit.py --output qualification-layout-v128.json
exit /b %ERRORLEVEL%
