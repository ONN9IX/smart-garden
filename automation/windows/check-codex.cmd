@echo off
rem Runs a read-only preflight on Windows. No elevated rights needed.
powershell.exe -NoProfile -File "%~dp0check-codex.ps1" -CheckCloud
set "code=%ERRORLEVEL%"
echo.
if not "%code%"=="0" echo Some prerequisites need attention; no tasks were started.
pause
exit /b %code%
