# ==============================================================================
# DeployDock — Atualizador Rápido da VM na Oracle Cloud (Windows PowerShell)
# Uso: .\update-oracle.ps1
# ==============================================================================
param(
    [string]$VmIp = "147.15.0.139",
    [string]$VmUser = "ubuntu"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  DeployDock — Atualizando Produção na Oracle ($VmIp)  " -ForegroundColor Cyan
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
    Write-Host "[ERRO] Chave SSH não encontrada em ~/.ssh/oracle_deploydock.key nem em Downloads!" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Empacotando código local (preservando .env de produção)..." -ForegroundColor Yellow
$TempTar = "$env:TEMP\deploydock-update.tar.gz"
if (Test-Path $TempTar) { Remove-Item $TempTar -Force }

tar --exclude=".git" `
    --exclude=".env" `
    --exclude="repos" `
    --exclude="node_modules" `
    --exclude=".venv" `
    --exclude="venv" `
    --exclude=".ruff_cache" `
    --exclude="__pycache__" `
    --exclude="deploydock.db" `
    --exclude="deploydock-benchmark-suite" `
    -czf $TempTar .

Write-Host "[2/3] Enviando pacote via SCP para $VmUser@$VmIp..." -ForegroundColor Yellow
scp -o StrictHostKeyChecking=no -i "$SshKey" "$TempTar" "${VmUser}@${VmIp}:~/deploydock-update.tar.gz"
Remove-Item $TempTar -Force

Write-Host "[3/3] Reconstruindo e reiniciando contêineres na VM..." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no -i "$SshKey" "${VmUser}@${VmIp}" "mkdir -p ~/DeployDock && tar -xzf ~/deploydock-update.tar.gz -C ~/DeployDock && rm -f ~/deploydock-update.tar.gz && cd ~/DeployDock && sed -i 's/\r$//' *.sh && chmod +x *.sh && sudo docker compose up -d --build && sudo docker image prune -f && sudo docker compose ps"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  DeployDock atualizado com sucesso na Oracle Cloud!" -ForegroundColor Green
Write-Host "  Painel: http://painel.$VmIp.sslip.io" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
