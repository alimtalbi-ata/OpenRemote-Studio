@echo off
setlocal
cd /d "%~dp0.."
set QT_QPA_PLATFORM=offscreen
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv || exit /b 10
)
.venv\Scripts\python.exe -m pip install -r Application\requirements.txt || exit /b 11
.venv\Scripts\python.exe 02-Compilation\qualify_qt.py || exit /b 12
set PYTHONPATH=%CD%\Application
.venv\Scripts\python.exe -m unittest discover -s Application\tests -p "test_*.py" || exit /b 13
 echo QUALIFICATION_PYTHON_QT=PASS
exit /b 0
