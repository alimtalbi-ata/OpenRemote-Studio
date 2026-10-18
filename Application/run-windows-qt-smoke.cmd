@echo off
setlocal
cd /d "%~dp0"
if exist "qualification-qt-smoke.json" (
  echo ERROR: Report exists; move it before rerunning.
  exit /b 3
)
where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python launcher not found.
  exit /b 2
)
py -3 windows_gui_smoke.py --output qualification-qt-smoke.json --timeout 20
if errorlevel 1 (
  echo Qt smoke FAILED or dependency missing. See qualification-qt-smoke.json.
  exit /b 4
)
echo Qt minimal startup passed; full GUI and network scenarios remain untested.
endlocal
