param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

& $Python -m pip install pyinstaller
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name PA450-Daily-Review-UI `
    --add-data "src/ui_app/assets/index.html;ui_app/assets" `
    src/ui.py

Write-Host "Built exe: dist\PA450-Daily-Review-UI.exe"
Write-Host "Run it with a local output folder beside the exe, or pass --data-dir when launching from a shortcut/command line."
