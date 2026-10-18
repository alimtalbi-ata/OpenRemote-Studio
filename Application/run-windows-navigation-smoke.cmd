@echo off
setlocal
cd /d "%~dp0"
python windows_navigation_smoke.py --output qualification-navigation-v126.json
exit /b %ERRORLEVEL%
