@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
if not "%OS%"=="Windows_NT" (echo Windows 10/11 x64 required & exit /b 1)
echo [OpenRemote Studio] Automatic Windows build - current VERSION.txt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap-and-build.ps1" %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo BUILD FAILED - code %RESULT%
exit /b %RESULT%
