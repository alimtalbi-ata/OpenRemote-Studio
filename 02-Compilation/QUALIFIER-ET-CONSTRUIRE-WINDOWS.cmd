@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
set "PYTHONUTF8=1"
set "QT_QPA_PLATFORM=offscreen"
py -3 VERIFY-RELEASE.py
if errorlevel 1 (echo BLOCK: release integrity & exit /b 9)
where py >nul 2>nul
if errorlevel 1 (echo BLOCK: Python launcher not found & exit /b 10)
py -3 -m venv .build-venv
if errorlevel 1 exit /b 11
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 12
python -m pip install -r Application\requirements.txt pyinstaller
if errorlevel 1 exit /b 13
python 02-Compilation\qualify_qt.py
if errorlevel 1 (echo BLOCK: Qt tests failed or skipped & exit /b 14)
python -m unittest discover -s Application\tests -p "test_*.py"
if errorlevel 1 (echo BLOCK: regression suite failed & exit /b 15)
python -m PyInstaller --noconfirm --clean --onedir --windowed --name OpenRemoteStudio --paths Application Application\qt_app.py
if errorlevel 1 exit /b 16
if not exist dist\OpenRemoteStudio\OpenRemoteStudio.exe (echo BLOCK: exe missing & exit /b 17)
echo PASS: Windows application built in dist\OpenRemoteStudio
exit /b 0
