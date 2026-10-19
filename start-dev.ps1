# Iniciar DeployDock via WSL (Ubuntu)
Write-Host "Iniciando DeployDock via WSL..." -ForegroundColor Cyan

$winPath = $PSScriptRoot -replace '\\', '/'
$wslPath = (wsl -d Ubuntu -- wslpath -a "$winPath").Trim()
wsl -d Ubuntu -- bash -c "cd '$wslPath' && chmod +x start-dev.sh && ./start-dev.sh"

