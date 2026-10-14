#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "\033[1;36m==============================================\033[0m"
echo -e "\033[1;36m  Iniciando DeployDock (Dev Mode - Linux)    \033[0m"
echo -e "\033[1;36m==============================================\033[0m"

# 1. PostgreSQL & Traefik via Docker
echo -e "\033[1;33m[1/3] Verificando PostgreSQL e Traefik (Docker)...\033[0m"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db traefik

# 2. Iniciar Backend
echo -e "\033[1;33m[2/3] Iniciando Backend FastAPI (Porta 8000)...\033[0m"
cd "$PROJECT_ROOT/backend"
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual Python..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# 3. Iniciar Frontend
echo -e "\033[1;33m[3/3] Iniciando Frontend Vite (Porta 3000)...\033[0m"
cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ]; then
    echo "Instalando dependências do frontend..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

cleanup() {
    echo -e "\n\033[1;31mEncerrando serviços DeployDock...\033[0m"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    wait $FRONTEND_PID 2>/dev/null || true
    echo -e "\033[1;32mServiços encerrados com sucesso!\033[0m"
}

trap cleanup INT TERM EXIT

echo ""
echo -e "\033[1;32m🚀 DeployDock iniciado com sucesso!\033[0m"
echo -e "   Frontend:           \033[1;34mhttp://localhost:3000\033[0m"
echo -e "   Backend API / Docs: \033[1;34mhttp://localhost:8000/docs\033[0m"
echo -e "   Pressione \033[1;33mCtrl+C\033[0m para encerrar."
echo ""

wait
