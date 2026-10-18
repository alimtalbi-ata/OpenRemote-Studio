@echo off
setlocal
cd /d "%~dp0"
python windows_accessibility_smoke.py --output qualification-accessibility-v127.json
exit /b %ERRORLEVEL%
