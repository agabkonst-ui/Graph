@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUTF8=1
set PYTHONDONTWRITEBYTECODE=1
if defined PYTHON_EXE (
    "%PYTHON_EXE%" -B -m unittest discover -s tests -v
    exit /b
)
py -3 -B -m unittest discover -s tests -v
exit /b %errorlevel%
