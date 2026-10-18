@echo off
setlocal
cd /d "%~dp0"
py -3 windows_qa_campaign.py --output qualification-windows-campaign-v132.json
exit /b %ERRORLEVEL%
