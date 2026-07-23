$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunBat = Join-Path $ProjectRoot "run.bat"

if (-not (Test-Path $RunBat)) {
  throw "run.bat was not found: $RunBat"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutName = "$([char]0x4e1a)$([char]0x7ee9)$([char]0x8868)$([char]0x683c)$([char]0x751f)$([char]0x6210)$([char]0x5de5)$([char]0x5177).lnk"
$ShortcutPath = Join-Path $Desktop $ShortcutName

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $RunBat
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = $ShortcutName.Replace(".lnk", "")
$Shortcut.Save()

Write-Host "Desktop shortcut created:"
Write-Host $ShortcutPath
