# 🐳 DeployDock — Status do Desenvolvimento

> **Última atualização**: 25/09/2026 — 20:30  
> **Conversa anterior**: Implementação inicial completa (backend + frontend + infra)

---

## ✅ O que já foi feito

### Backend (Python/FastAPI) — COMPLETO
- [x] Estrutura do projeto FastAPI com 37 arquivos
- [x] Configuração (`core/config.py`) com Pydantic Settings + `.env`
- [x] Banco de dados PostgreSQL async (`asyncpg` + SQLAlchemy 2.0)
- [x] 3 modelos: `Project`, `Deployment`, `EnvironmentVariable` (UUID, timestamps)
- [x] Schemas Pydantic v2 para todos os modelos
- [x] `DockerService` — wrapper completo do Docker SDK:
  - List/get/start/stop/restart/remove containers
  - Stream logs (thread daemon + asyncio.Queue)
  - Métricas CPU/RAM/Rede (fórmula correta de cgroups)
  - Build images, list/remove images, volumes, networks
  - System info, prune
- [x] `GitService` — clone/pull via GitPython
- [x] `DeployOrchestrator` — pipeline completo:
  - Webhook → Clone → Build (streaming) → Container Swap → Health Check → Rollback automático
- [x] `WebSocketManager` — gerenciador de conexões por tópico
- [x] Validação HMAC-SHA256 dos webhooks GitHub (`hmac.compare_digest`)
- [x] Criptografia Fernet para variáveis de ambiente
- [x] 6 routers de API: containers, projects, deployments, webhooks, system, ws
- [x] Endpoint `/health` para monitoramento

### Frontend (Vue.js 3 + TypeScript + Tailwind v4) — COMPLETO + BUILD OK ✅
- [x] Vite + Vue 3 + TypeScript configurado
- [x] Tailwind CSS v4 com tema Docker dark-mode customizado
- [x] Layout: Sidebar (glassmorphism) + Topbar + MainLayout com transições
- [x] 6 páginas: Dashboard, ContainerList, ContainerDetail, Projects, Deployments, Settings
- [x] Componentes: ContainerCard, ContainerTable, LogViewer (xterm.js), MetricsChart (vue-chartjs), StatusBadge, StatCard, DeployTimeline, DeployPipeline, ContainerActions
- [x] Composables: useWebSocket (auto-reconnect), useContainerMetrics (FIFO buffer), useApi
- [x] API client completo (`services/api.ts`) apontando para `/api/v1/*`
- [x] `npm run build` passa sem erros

### Infraestrutura — COMPLETO
- [x] `docker-compose.yml` — 3 serviços (backend, frontend/nginx, postgres)
- [x] `docker-compose.dev.yml` — override com hot reload
- [x] `backend/Dockerfile` — multi-stage (dev + prod)
- [x] `frontend/Dockerfile` — multi-stage (dev + build + nginx)
- [x] `frontend/nginx.conf` — proxy API + WebSocket + gzip + SPA fallback
- [x] `.env.example`, `.gitignore`, `README.md`

---

## ⚠️ O que falta fazer / melhorar

### Prioridade Alta
1. **Alembic (migrações de banco)** — ainda não configurado. Precisamos de:
   - `alembic init alembic` no diretório backend
   - Configurar `env.py` para usar o async engine
   - Gerar a migração inicial: `alembic revision --autogenerate -m "initial"`
   
2. **Testar o sistema rodando** — subir com Docker Compose e verificar:
   - Backend conecta no PostgreSQL
   - Frontend carrega e exibe o dashboard
   - Listagem de containers funciona
   - WebSocket de logs e métricas funciona

3. **Ajustar API client do frontend** — as URLs da API (`/api/v1/containers`, etc.) precisam bater exatamente com as rotas do backend. Verificar se os campos retornados pela API batem com os tipos TypeScript.

### Prioridade Média
4. **Testes automatizados** — pytest + pytest-asyncio para o backend:
   - `test_webhook_security.py` — verificar validação HMAC
   - `test_docker_service.py` — mock do Docker SDK
   - `test_projects_api.py` — CRUD de projetos
   
5. **Topbar dinâmica** — os valores de "12 Running", "CPU: 14%", "RAM: 42%" no `AppTopbar.vue` estão hardcoded. Precisam buscar do `/api/v1/system/info` e atualizar periodicamente.

6. **Projetos → Deploy trigger** — o botão "Deploy New Project" no Dashboard e o "Trigger Deploy" na page de Projects precisam estar wired com a API.

7. **Env vars UI** — a tela de Projects precisa de um modal/seção para gerenciar variáveis de ambiente encriptadas.

### Prioridade Baixa
8. **Responsividade mobile** — sidebar collapsível já tem estrutura, mas precisa testar em telas pequenas
9. **Notificações toast** — substituir `alert()` e `confirm()` por componentes de notificação estilizados
10. **Tema claro** — toggle dark/light mode (opcional para o TCC)
11. **Documentação Swagger** — adicionar descrições detalhadas nos endpoints FastAPI

---

## 📁 Estrutura do Projeto (referência rápida)

```
tcc/
├── docker-compose.yml / docker-compose.dev.yml
├── .env.example / .gitignore / README.md
│
├── backend/
│   ├── Dockerfile / requirements.txt
│   └── app/
│       ├── main.py                          # FastAPI app
│       ├── core/  (config, security, logging)
│       ├── db/    (session, base)
│       ├── models/  (project, deployment, environment)
│       ├── schemas/ (project, deployment, container, webhook)
│       ├── services/ (docker_service, git_service, deploy_orchestrator, websocket_manager)
│       └── api/v1/endpoints/ (containers, projects, deployments, webhooks, system, ws)
│
└── frontend/
    ├── Dockerfile / nginx.conf / package.json / vite.config.ts
    └── src/
        ├── assets/main.css          # Tailwind v4 + tema
        ├── components/              # layout/, containers/, deployments/, common/
        ├── composables/             # useWebSocket, useContainerMetrics, useApi
        ├── pages/                   # 6 páginas
        ├── router/index.ts
        └── services/ (api.ts, types.ts)
```

---

## 🚀 Como continuar

```bash
# 1. Para rodar tudo com Docker:
cp .env.example .env
docker-compose up --build

# 2. Para dev local (backend):
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Para dev local (frontend):
cd frontend
npm install   # já feito, node_modules existe
npm run dev   # http://localhost:3000

# 4. Swagger da API:
# http://localhost:8000/docs
```

---

## 🔑 Decisões técnicas tomadas

| Decisão | Justificativa |
|---|---|
| `asyncio.to_thread()` para docker-py | Docker SDK é síncrono — isola operações bloqueantes |
| Thread daemon + asyncio.Queue para log streaming | Evita bloquear o event loop do FastAPI ao fazer `follow=True` |
| Fernet para env vars | Criptografia simétrica simples, adequada para o escopo do TCC |
| Tailwind v4 CSS-first (sem tailwind.config.js) | Simplifica config, usa `@theme` direto no CSS |
| vue-chartjs (não Recharts) | Recharts é React-only; vue-chartjs é o equivalente para Vue |
| xterm.js para logs | Renderiza ANSI colors, alta performance via Canvas, zero re-renders |
| PostgreSQL (não SQLite) | Escolha do aluno — robusto, escalável, roda em contêiner dedicado |
