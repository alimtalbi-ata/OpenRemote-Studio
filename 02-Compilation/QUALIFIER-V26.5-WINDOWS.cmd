@echo off
setlocal
cd /d "%~dp0..\Application" || exit /b 2
python -c "import PySide6; print('PySide6 OK')" || exit /b 10
python "%~dp0qualify_qt.py" || exit /b 11
python -m unittest discover -s tests -v || exit /b 12
echo QUALIFICATION PYTHON OK - Windows GUI and network tests remain manual.
exit /b 0
