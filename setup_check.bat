@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo [1/4] Checking Python
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python 3.10 or newer.
) else (
  python --version
)

echo.
echo [2/4] Checking lark-cli
where lark-cli >nul 2>nul
if errorlevel 1 (
  echo lark-cli was not found. Ask WorkBuddy/Codex to install it using README.
) else (
  lark-cli --version
)

echo.
echo [3/4] Checking Feishu authorization
where lark-cli >nul 2>nul
if errorlevel 1 (
  echo Skipped because lark-cli is missing.
) else (
  lark-cli auth status --json --verify
)

echo.
echo [4/4] Checking config
if exist "config\config.json" (
  echo Found config\config.json
) else (
  echo config\config.json was not found. Copy config\config.example.json to config\config.json before first use.
)

echo.
pause
