@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"
if errorlevel 1 (
  echo Failed to create desktop shortcut.
  pause
  exit /b 1
)

echo.
echo Desktop shortcut is ready.
pause
