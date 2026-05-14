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
Write-Host "Default file root: project folder (parent of dist when running the bundled exe)."
Write-Host "Default CSV/AI JSON/feedback folder: <file root>\output; Review UI can still choose another feedback folder."
