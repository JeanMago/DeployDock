#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "\033[1;36m==============================================\033[0m"
echo -e "\033[1;36m  Iniciando DeployDock (Dev Mode - WSL/Linux) \033[0m"
echo -e "\033[1;36m==============================================\033[0m"

# Garantir que o serviço Docker está ativo no WSL
if ! docker info >/dev/null 2>&1; then
    echo -e "\033[1;33mIniciando daemon do Docker no WSL...\033[0m"
    wsl.exe -d "${WSL_DISTRO_NAME:-Ubuntu}" -u root -- systemctl start docker 2>/dev/null || sudo service docker start
fi

# Extrair credenciais do PostgreSQL do .env (sem quebrar JSON do CORS_ORIGINS)
if [ -f "$PROJECT_ROOT/.env" ]; then
    POSTGRES_DB=$(grep -E '^POSTGRES_DB=' "$PROJECT_ROOT/.env" | cut -d '=' -f2- | tr -d '\r"' || true)
    POSTGRES_USER=$(grep -E '^POSTGRES_USER=' "$PROJECT_ROOT/.env" | cut -d '=' -f2- | tr -d '\r"' || true)
    POSTGRES_PASSWORD=$(grep -E '^POSTGRES_PASSWORD=' "$PROJECT_ROOT/.env" | cut -d '=' -f2- | tr -d '\r"' || true)
fi

# Ajustar variáveis para execução local no host WSL conectando ao Postgres no Docker
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER:-deploydock}:${POSTGRES_PASSWORD:-deploydock_secret_password}@localhost:5432/${POSTGRES_DB:-deploydock}"
export REPOS_BASE_PATH="${PROJECT_ROOT}/repos"
mkdir -p "$REPOS_BASE_PATH"

# 1. PostgreSQL & Traefik via Docker
echo -e "\033[1;33m[1/3] Verificando PostgreSQL e Traefik (Docker)...\033[0m"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db traefik

# 2. Iniciar Backend
echo -e "\033[1;33m[2/3] Iniciando Backend FastAPI (Porta 8000)...\033[0m"
cd "$PROJECT_ROOT/backend"
if [ ! -f "venv/bin/uvicorn" ]; then
    echo "Configurando ambiente virtual Python (Linux/WSL)..."
    rm -rf venv
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 3. Iniciar Frontend
echo -e "\033[1;33m[3/3] Iniciando Frontend Vite (Porta 3000)...\033[0m"
cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ] || [ ! -d "node_modules/@esbuild/linux-x64" ]; then
    echo "Instalando dependências do frontend para Linux/WSL..."
    npm install --include=optional
fi

npm run dev -- --host 0.0.0.0 --port 3000 &
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
echo -e "\033[1;32m🚀 DeployDock iniciado com sucesso no WSL!\033[0m"
echo -e "   Frontend:           \033[1;34mhttp://localhost:3000\033[0m"
echo -e "   Backend API / Docs: \033[1;34mhttp://localhost:8000/docs\033[0m"
echo -e "   Pressione \033[1;33mCtrl+C\033[0m para encerrar."
echo ""

wait
