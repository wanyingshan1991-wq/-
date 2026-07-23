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

if not exist "config\config.json" (
  echo config\config.json was not found.
  echo Copying config\config.example.json to config\config.json...
  copy "config\config.example.json" "config\config.json" >nul
  echo Please review config\config.json, then run this file again.
  pause
  exit /b 1
)

echo.
set /p TARGET_MONTH=Input target month number, for example 8: 
if "%TARGET_MONTH%"=="" (
  echo No month input. Canceled.
  pause
  exit /b 1
)

echo.
echo Generating policy revision for month %TARGET_MONTH%...
python "scripts\generate_policy_revision.py" --month %TARGET_MONTH%

echo.
pause
