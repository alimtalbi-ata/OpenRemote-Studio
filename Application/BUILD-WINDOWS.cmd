@echo off
call "%~dp0windows\BUILD-WINDOWS.cmd" %*
exit /b %ERRORLEVEL%
