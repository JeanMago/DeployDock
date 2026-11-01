# Expor o DeployDock (porta 3000) na internet externa via Cloudflare Quick Tunnel no WSL
# (Gratuito, sem conta, sem instalar nada no Windows, sem pedir senha de IP e sem tela branca)
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  DeployDock - Tunel Externo HTTPS (Sem Conta / Sem Senha)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[1] Credenciais do Painel DeployDock: " -NoNewline
Write-Host "admin / admin123" -ForegroundColor Green
Write-Host "[2] Iniciando tunel HTTPS direto para http://127.0.0.1:3000..." -ForegroundColor Cyan
Write-Host "    Copie o link https://....trycloudflare.com exibido abaixo:`n" -ForegroundColor Yellow

wsl -d Ubuntu -- bash -c "if [ ! -f /tmp/cloudflared ]; then curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared && chmod +x /tmp/cloudflared; fi && /tmp/cloudflared tunnel --url http://127.0.0.1:3000"
