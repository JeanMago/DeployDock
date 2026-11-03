# ==============================================================================
# DeployDock - Atualizador Rapido da VM na Oracle Cloud (Windows PowerShell)
# Uso: .\update-oracle.ps1
# ==============================================================================
param(
    [string]$VmIp = "147.15.0.139",
    [string]$VmUser = "ubuntu"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  DeployDock - Atualizando Producao na Oracle ($VmIp)  " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Localiza a chave SSH (no ~/.ssh ou na pasta Downloads)
$CandidateKeys = @(
    "$HOME\.ssh\oracle_deploydock.key",
    "$HOME\Downloads\ssh-key-2026-10-30 (1).key",
    "$HOME\Downloads\ssh-key-2026-10-30.key"
)

$SshKey = $null
foreach ($Key in $CandidateKeys) {
    if (Test-Path $Key) {
        $SshKey = $Key
        break
    }
}

if (-not $SshKey) {
    Write-Host "[ERRO] Chave SSH nao encontrada em ~/.ssh/oracle_deploydock.key nem em Downloads!" -ForegroundColor Red
    exit 1
}

# Se os arquivos estáticos do frontend não estiverem compilados, compila localmente em 4s
if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "[0/3] Compilando frontend localmente para economizar memoria na VPS..." -ForegroundColor Yellow
    npm --prefix frontend run build
}

Write-Host "[1/3] Empacotando codigo local (preservando .env de producao)..." -ForegroundColor Yellow
$TempTar = "$env:TEMP\deploydock-update.tar.gz"
if (Test-Path $TempTar) { Remove-Item $TempTar -Force }

tar --exclude=".git" `
    --exclude=".env" `
    --exclude="repos" `
    --exclude="node_modules" `
    --exclude=".venv" `
    --exclude="venv" `
    --exclude=".ruff_cache" `
    --exclude=".pytest_cache" `
    --exclude="__pycache__" `
    --exclude="deploydock.db" `
    -czf $TempTar .

Write-Host "[2/3] Enviando pacote via SCP para $VmUser@$VmIp..." -ForegroundColor Yellow
scp -o StrictHostKeyChecking=no -i "$SshKey" "$TempTar" "${VmUser}@${VmIp}:~/deploydock-update.tar.gz"
Remove-Item $TempTar -Force

Write-Host "[3/3] Reconstruindo e reiniciando conteineres na VM..." -ForegroundColor Yellow
$RemoteCmd = @'
mkdir -p ~/DeployDock && \
tar -xzf ~/deploydock-update.tar.gz -C ~/DeployDock && \
rm -f ~/deploydock-update.tar.gz && \
cd ~/DeployDock && \
tr -d '\r' < deploy-prod.sh > deploy-prod.sh.tmp && mv deploy-prod.sh.tmp deploy-prod.sh && chmod +x *.sh && \
sudo docker compose up -d --build && \
if sudo docker ps -q -f name=deploydock_testadorde-deploy | grep -q .; then \
    sudo docker cp ~/DeployDock/deploydock-benchmark-suite/app/probes/deploydock_api_tester.py deploydock_testadorde-deploy:/app/app/probes/deploydock_api_tester.py && \
    sudo docker restart deploydock_testadorde-deploy; \
fi && \
sudo docker cp ~/DeployDock/deploydock-benchmark-suite/app/probes/deploydock_api_tester.py deploydock-backend:/app/repos/0d62de3d-bfd4-408d-a301-e29074bf25de/app/probes/deploydock_api_tester.py 2>/dev/null || true && \
sudo docker image prune -f && \
sudo docker compose ps
'@

ssh -o StrictHostKeyChecking=no -i "$SshKey" "${VmUser}@${VmIp}" $RemoteCmd

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  DeployDock atualizado com sucesso na Oracle Cloud!" -ForegroundColor Green
Write-Host "  Painel: https://painel.$VmIp.sslip.io" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
