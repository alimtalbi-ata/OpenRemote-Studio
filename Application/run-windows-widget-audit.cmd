@echo off
setlocal
cd /d "%~dp0"
python windows_widget_audit.py --output qualification-widget-v130.json
exit /b %errorlevel%
