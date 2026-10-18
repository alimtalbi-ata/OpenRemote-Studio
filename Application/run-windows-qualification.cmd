@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python launcher py not found.
  exit /b 2
)
if exist "qualification-windows.json" (
  echo ERROR: qualification-windows.json already exists. Move it before rerunning.
  exit /b 3
)
py -3 windows_preflight.py --root "." --output "qualification-windows.json"
if errorlevel 1 exit /b 4
echo Preflight complete: qualification-windows.json
 echo GUI and live network scenarios have NOT been executed.
endlocal
