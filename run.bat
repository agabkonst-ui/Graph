@echo off
py -3 -c "import sys" >nul 2>&1
if errorlevel 1 (
    python -B -X utf8 "%~dp0src\main.py" %*
) else (
    py -3 -B -X utf8 "%~dp0src\main.py" %*
)
exit /b %errorlevel%
