@echo off
echo ==============================================
echo   Iniciando DeployDock via WSL (Ubuntu)
echo ==============================================

wsl -d Ubuntu -- bash -c "cd \"$(wslpath -a '%~dp0')\" && chmod +x start-dev.sh && ./start-dev.sh"
