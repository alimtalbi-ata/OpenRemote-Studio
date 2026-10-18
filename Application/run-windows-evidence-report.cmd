@echo off
setlocal
cd /d "%~dp0"
py -3 qa_evidence_report.py --input qualification-windows-campaign-v132.json --output qualification-evidence-v133.html
exit /b %errorlevel%
