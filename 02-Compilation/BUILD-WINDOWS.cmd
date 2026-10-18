@echo off
setlocal
cd /d "%~dp0.."
call Application\BUILD-WINDOWS.cmd
exit /b %errorlevel%
