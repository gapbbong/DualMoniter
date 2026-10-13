$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop "01_듀얼모니터_교사_대시보드_실행.lnk"
$wshell = New-Object -ComObject WScript.Shell
$shortcut = $wshell.CreateShortcut($lnkPath)
$shortcut.TargetPath = "$PSScriptRoot\01_듀얼모니터_교사_대시보드_실행.bat"
$shortcut.WorkingDirectory = "$PSScriptRoot"
$shortcut.Save()
Write-Host "Shortcut created at: $lnkPath"
