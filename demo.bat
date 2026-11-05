@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUTF8=1
set PYTHONDONTWRITEBYTECODE=1
if defined PYTHON_EXE (
    "%PYTHON_EXE%" -B scripts/demo.py
    exit /b
)
py -3 -B scripts/demo.py
exit /b %errorlevel%
