$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunBat = Join-Path $ProjectRoot "run.bat"

if (-not (Test-Path $RunBat)) {
  throw "run.bat was not found: $RunBat"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$BaseName = "$([char]0x4e1a)$([char]0x7ee9)$([char]0x8868)$([char]0x683c)$([char]0x751f)$([char]0x6210)$([char]0x5de5)$([char]0x5177)"
$ShortcutPath = Join-Path $Desktop "$BaseName.lnk"
$LauncherPath = Join-Path $Desktop "$BaseName.bat"

try {
  $Shell = New-Object -ComObject WScript.Shell
  $Shortcut = $Shell.CreateShortcut($ShortcutPath)
  $Shortcut.TargetPath = $RunBat
  $Shortcut.WorkingDirectory = $ProjectRoot
  $Shortcut.Description = $BaseName
  $Shortcut.Save()

  Write-Host "Desktop shortcut created:"
  Write-Host $ShortcutPath
} catch {
  $Launcher = @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d ""$ProjectRoot""",
    "call ""$RunBat"""
  )
  Set-Content -LiteralPath $LauncherPath -Value $Launcher -Encoding ASCII
  Write-Host "Could not create .lnk shortcut. Created desktop .bat launcher instead:"
  Write-Host $LauncherPath
}
