# Build the local PA450 Review UI into a single Windows executable.
#
# Usage from PowerShell:
#   .\scripts\build-ui-exe.ps1
#   .\scripts\build-ui-exe.ps1 -Python .venv\Scripts\python.exe
#
# The --add-data entries below bundle the static HTML/CSS/JS assets that
# src/ui.py serves at runtime. Keep this list in sync when UI asset files move.
param(
    [string]$Python = "python"
)

# Stop on the first failed command so engineers do not miss a broken build.
$ErrorActionPreference = "Stop"

# Install/upgrade PyInstaller in the selected Python environment before build.
& $Python -m pip install pyinstaller

# Produce dist\PA450-Daily-Review-UI.exe as a one-file executable for operators.
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name PA450-Daily-Review-UI `
    --add-data "src/ui_app/assets/index.html;ui_app/assets" `
    --add-data "src/ui_app/assets/styles.css;ui_app/assets" `
    --add-data "src/ui_app/assets/app.js;ui_app/assets" `
    src/ui.py

Copy-Item ui_settings.example.json dist\ui_settings.json -Force

Write-Host "Built exe: dist\PA450-Daily-Review-UI.exe"
Write-Host "Copied dashboard settings: dist\ui_settings.json"
Write-Host "Double-click the exe. Remote clients can open http://<this-windows-lan-ip>:8765 after Windows Firewall allows the port."
