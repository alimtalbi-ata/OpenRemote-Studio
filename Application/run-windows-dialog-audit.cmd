@echo off
setlocal
cd /d "%~dp0"
python windows_dialog_audit.py --output qualification-dialog-v131.json
exit /b %ERRORLEVEL%
