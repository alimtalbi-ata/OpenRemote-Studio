@echo off
setlocal
cd /d "%~dp0"
python windows_main_smoke.py --output qualification-main-smoke.json
exit /b %ERRORLEVEL%
