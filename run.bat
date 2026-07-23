@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python 3.10+ or ask WorkBuddy/Codex to run setup_check.bat.
  pause
  exit /b 1
)

where lark-cli >nul 2>nul
if errorlevel 1 (
  echo lark-cli was not found. Please install and authorize lark-cli first.
  pause
  exit /b 1
)

python "scripts\main.py"

echo.
pause
