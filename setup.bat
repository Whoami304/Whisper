@echo off
setlocal
cd /d "%~dp0"

rem Find Python: prefer the "py" launcher, fall back to "python".
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
    echo Python 3 was not found. Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment in .venv ...
    %PY% -m venv .venv || goto :fail
)

echo Installing requirements ...
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt || goto :fail

echo.
echo Done. Interpreter for PyCharm:
echo   %CD%\.venv\Scripts\python.exe
echo Start the app with run.bat
pause
exit /b 0

:fail
echo.
echo Setup failed - see the messages above.
pause
exit /b 1
