@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo [1/4] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python 3.10+ first.
  pause
  exit /b 1
)
python --version

echo.
echo [2/4] Checking lark-cli...
where lark-cli >nul 2>nul
if errorlevel 1 (
  echo lark-cli was not found. Please install and authorize lark-cli first.
  pause
  exit /b 1
)
lark-cli --version

echo.
echo [3/4] Running configuration wizard...
python "scripts\main.py" configure
if errorlevel 1 (
  echo Configuration failed.
  pause
  exit /b 1
)

echo.
echo [4/4] Creating desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"
if errorlevel 1 (
  echo Failed to create desktop shortcut.
  pause
  exit /b 1
)

echo.
echo First-time setup is complete.
echo You can now use the desktop shortcut: 业绩表格生成工具
pause
