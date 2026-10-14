@echo off
echo ==============================================
echo   Iniciando DeployDock (Backend + Frontend)
echo ==============================================

echo [1/2] Iniciando Backend FastAPI (Porta 8000)...
start "DeployDock Backend" cmd /k "cd /d %~dp0backend && .\venv\Scripts\activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Iniciando Frontend Vite (Porta 3000)...
start "DeployDock Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo DeployDock em execucao!
echo Frontend: http://localhost:3000
echo Backend API / Swagger: http://localhost:8000/docs
echo.
