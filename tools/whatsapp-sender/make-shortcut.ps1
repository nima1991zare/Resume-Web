# Creates (or refreshes) the desktop shortcut for the WhatsApp sender.
# Run it again after moving the folder or reinstalling Windows.
$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $root "start.cmd"
$desk   = [Environment]::GetFolderPath("Desktop")
$lnk    = Join-Path $desk "WhatsApp Sender.lnk"

$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath       = $target
$s.WorkingDirectory = $root
$s.Description      = "Start the Project Finder WhatsApp sender"
$s.IconLocation     = "C:\Program Files\Google\Chrome\Application\chrome.exe,0"
$s.WindowStyle      = 1
$s.Save()

Write-Host "Shortcut created:"
Write-Host "  $lnk"
Write-Host "  -> $target"
