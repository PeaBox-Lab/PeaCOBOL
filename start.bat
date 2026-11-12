@echo off
setlocal
cd /d "%~dp0"

echo PeaCOBOL 1.0.0 - Windows launcher
set "PYTHON_CMD="
where py >nul 2>nul && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  echo ERROR: Python 3.10 or newer was not found.
  echo Install Python, enable "Add Python to PATH", and run start.bat again.
  pause
  exit /b 1
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo ERROR: PeaCOBOL requires Python 3.10 or newer.
  pause
  exit /b 1
)

echo Starting the secure local GUI...
echo Keep this window open. Press Ctrl+C to stop PeaCOBOL.
%PYTHON_CMD% -m peacobol.server --root "%~dp0" --port 8765 --open-browser
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo PeaCOBOL stopped with exit code %EXIT_CODE%.
  pause
)
exit /b %EXIT_CODE%
