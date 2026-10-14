#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "\033[1;36m================================================\033[0m"
echo -e "\033[1;36m   DeployDock - Modo Produção (Docker Compose)   \033[0m"
echo -e "\033[1;36m================================================\033[0m"

# Subir todos os serviços em segundo plano com build
docker compose up -d --build

echo ""
echo -e "\033[1;32m🚀 DeployDock iniciado em produção com sucesso!\033[0m"
echo -e "   Frontend (Nginx):   \033[1;34mhttp://localhost\033[0m"
echo -e "   Backend API / Docs: \033[1;34mhttp://localhost:8000/docs\033[0m"
echo -e "   Ver logs:           \033[1;33mdocker compose logs -f\033[0m"
echo -e "   Para parar:         \033[1;33mdocker compose down\033[0m"
echo ""
