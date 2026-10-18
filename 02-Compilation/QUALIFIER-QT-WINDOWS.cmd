@echo off
setlocal
cd /d "%~dp0..\Application" || exit /b 2
where py >nul 2>nul || (echo BLOCK: Python launcher introuvable & exit /b 2)
py -3 -m pip install -r requirements.txt || exit /b 3
set QT_QPA_PLATFORM=offscreen
py -3 "%~dp0qualify_qt.py" || exit /b 4
py -3 -m unittest discover -s tests -v || exit /b 5
echo PASS: Qt bridge and full regression suite
exit /b 0
