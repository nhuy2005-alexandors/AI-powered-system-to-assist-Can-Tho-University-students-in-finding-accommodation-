$ErrorActionPreference = 'Stop'

$workspace = "D:\Dev\Workspaces\Omni_Assistant"
$batPath   = Join-Path $workspace ".agent\scripts\omni-coop.bat"
$iconPath  = "$env:SystemRoot\System32\shell32.dll"

if (!(Test-Path $batPath)) {
    Write-Host "[X] omni-coop.bat not found at $batPath" -ForegroundColor Red
    exit 1
}

$desktop      = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Omni Co-op.lnk'

$WScript  = New-Object -ComObject WScript.Shell
$shortcut = $WScript.CreateShortcut($shortcutPath)
$shortcut.TargetPath       = "$env:ComSpec"
$shortcut.Arguments        = "/c `"$batPath`""
$shortcut.WorkingDirectory = $workspace
$shortcut.IconLocation     = "$iconPath,25"
$shortcut.Description      = "Omni Assistant - Claude+Gemini co-op launcher"
$shortcut.WindowStyle      = 1
$shortcut.Save()

Write-Host "[OK] Shortcut created:" -ForegroundColor Green
Write-Host "     $shortcutPath"
Write-Host ""
Write-Host "Double-click it any time to run the co-op loop."
