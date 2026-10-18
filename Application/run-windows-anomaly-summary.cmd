@echo off
setlocal
cd /d "%~dp0"
py -3 qa_anomaly_summary.py qualification-windows-campaign-v132.json --output qualification-anomalies-v134.json
exit /b %ERRORLEVEL%
