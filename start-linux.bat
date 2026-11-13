@echo off
setlocal
cd /d "%~dp0"
echo PeaCOBOL 1.1.0 - Linux via Windows Subsystem for Linux
where wsl.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: Windows Subsystem for Linux was not found.
  echo On a Linux computer, run: chmod +x start-linux.sh ^&^& ./start-linux.sh
  pause
  exit /b 1
)
for /f "delims=" %%I in ('wsl.exe wslpath -a "%~dp0"') do set "WSL_DIR=%%I"
wsl.exe sh "%WSL_DIR%/start-linux.sh"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
