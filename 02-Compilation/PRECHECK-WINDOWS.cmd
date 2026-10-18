@echo off
cd /d "%~dp0.."
where py || exit /b 2
py -3 -c "import sys; print(sys.version)" || exit /b 3
if not exist Application\qt_app.py exit /b 4
if not exist Application\requirements.txt exit /b 5
echo PRECHECK PASS - not a build or functional qualification
