# 🤖 AI_CONTEXT.md — Contexto Completo do Projeto DeployDock para IAs

> **Propósito deste arquivo:** Fornecer contexto técnico imediato, completo e estruturado para qualquer Assistente de IA (Antigravity, Claude, Cursor, Copilot, ChatGPT, Gemini) que venha a trabalhar neste repositório no futuro.
> **Última atualização:** Outubro de 2026

---

## 1. Visão Geral do Sistema

**DeployDock** é uma plataforma PaaS auto-hospedável e gerenciador de contêineres Docker com entrega contínua GitOps (similar ao Coolify, Portainer e CapRover), desenvolvida como Trabalho de Conclusão de Curso (TCC) em Ciência da Computação.

### Stack Principal
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0 (Async) + Pydantic v2 + Docker SDK (`docker-py`) + GitPython.
- **Banco de Dados:**
  - **Desenvolvimento local (`start-dev.sh` / `start-dev.ps1`):** SQLite assíncrono (`sqlite+aiosqlite:///./deploydock.db`) configurado automaticamente quando PostgreSQL não está rodando na porta 5432.
  - **Produção (`docker-compose.yml` / `deploy-prod.sh`):** PostgreSQL 16 (`postgresql+asyncpg://...`).
- **Frontend:** Vue 3 (Composition API `<script setup lang="ts">`) + TypeScript + Vite + Tailwind CSS v4 + Pinia + Vue Router + Xterm.js + Chart.js (`vue-chartjs`) + Lucide Vue Next.
- **Proxy Reverso & SSL:** Traefik v3 gerenciado via Docker Labels dinâmicas (`backend/app/core/routing.py`) com suporte a Let's Encrypt ACME (`APPS_TLS_ENABLED=true`) e redirecionamento automático HTTP → HTTPS.
- **Segurança Integrada:** Middleware WAF + Rate Limiting + Anti-Brute-Force + Security Headers (`backend/app/core/waf.py`).

---

## 2. Como Executar / Reiniciar o Projeto no Ambiente Atual

### Ambiente de Desenvolvimento (Windows + WSL Ubuntu)
O usuário executa o sistema no Windows usando **WSL (`Ubuntu`)** onde o Docker Engine, o Python `venv` e o Node/Vite rodam.
- **Script padrão para iniciar/reiniciar tudo em dev:**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\start-dev.ps1
  ```
  *(Internamente, `start-dev.ps1` chama `wsl -d Ubuntu -- bash ./start-dev.sh`, que mata processos antigos nas portas `8000` e `3000`, ativa o `backend/venv`, sobe o `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` e sobe o Vite `npm run dev -- --host 0.0.0.0 --port 3000`).*
- **Credenciais padrão de login criadas no startup (`backend/app/main.py`):**
  - **Usuário:** `admin`
  - **Senha:** `admin123` (configurável via `INITIAL_ADMIN_PASSWORD` no `.env`)

### Ambiente de Produção (Linux VPS — Oracle Cloud / Hostgrid)
- **Script automatizado:** `sudo ./deploy-prod.sh [dominio_opcional] [email_opcional]`
- **Orquestração:** `docker compose up -d --build` (usa `docker-compose.yml` com `traefik`, `postgres`, `backend`, `frontend`).
- **Guia detalhado:** `GUIA_DEPLOY_PRODUCAO_ORACLE_HOSTGRID.md`.

---

## 3. Arquitetura Detalhada do Backend (`backend/app/`)

```text
backend/app/
├── main.py                           # App FastAPI, lifespan (DB init + seed admin), CORS, SecurityMiddleware (WAF)
├── core/
│   ├── config.py                     # Settings Pydantic (DATABASE_URL, SECRET_KEY, APPS_BASE_DOMAIN, APPS_TLS_ENABLED, etc.)
│   ├── security.py                   # Hash de senha (PBKDF2-HMAC-SHA256), JWT (create_access_token, decode), Fernet (env vars)
│   ├── routing.py                    # Funções normalize_hostname() e build_traefik_labels() (HTTP + HTTPS redirect)
│   └── waf.py                        # SecurityEngine + SecurityMiddleware (WAF SQLi/XSS/Traversal/CmdInj, Rate Limit, IP Ban)
├── db/
│   ├── base.py                       # DeclarativeBase SQLAlchemy
│   └── session.py                    # AsyncEngine, AsyncSessionLocal e dependency get_db()
├── models/
│   ├── user.py                       # User (id, username, email, hashed_password, is_active, is_superuser)
│   ├── project.py                    # Project (name, repo_url, branch, deploy_mode, domain, container_id, status, webhook_secret...)
│   ├── deployment.py                 # Deployment (project_id, commit_sha, status, build_logs, duration_seconds, triggered_by...)
│   └── environment.py                # EnvironmentVariable (project_id, key, encrypted_value, is_secret)
├── schemas/                          # Schemas Pydantic v2 (project.py, deployment.py, container.py, auth.py, webhook.py)
├── services/
│   ├── docker_service.py             # Wrapper assíncrono do docker-py (containers, logs, stats, exec, file explorer, prune, quick-run)
│   ├── git_service.py                # Clone, pull, checkout de commit específico (para rollback) e metadados do commit
│   ├── deploy_orchestrator.py        # Pipeline GitOps: Clone → Auto-Dockerfile (se faltar) → Build/Compose → Swap → Healthcheck → Rollback
│   └── websocket_manager.py          # Pub/Sub WebSocket por tópicos
└── api/v1/
    ├── router.py                     # Agrega todas as rotas sob /api/v1
    └── endpoints/
        ├── auth.py                   # POST /login, GET /me, GET/POST /users, PUT /password, OAuth Device (GitHub/Google), /account, /admin/access
        ├── containers.py             # GET /containers, POST /run (Quick Launch), start/stop/restart/remove, GET /logs, GET /stats, GET /files, GET /files/content
        ├── projects.py               # CRUD de projetos, GET/PUT /env (variáveis .env), POST /deploy
        ├── deployments.py            # GET /deployments, GET /{id}/logs, POST /trigger, POST /rollback/{project_id}
        ├── system.py                 # GET /info (CPU/RAM/Disco host), GET /resources, POST /prune, GET /production-check, /notifications
        ├── security.py               # GET /summary, GET /events, POST /block-ip, DELETE /block-ip/{ip}, POST /config, DELETE /events
        ├── webhooks.py               # POST /github (Valida HMAC-SHA256 por projeto ou global e dispara deploy em background)
        └── ws.py                     # WS /ws/logs/{id}, WS /ws/stats/{id}, WS /ws/exec/{id} (terminal), WS /ws/deployments
├── services/
│   ├── docker_service.py             # Wrapper assíncrono Docker SDK (containers, stats, logs, exec, prune)
│   ├── deploy_orchestrator.py        # Pipeline de deploy GitOps (Clone -> Build -> Swap -> Check -> Rollback)
│   ├── account_service.py            # AccountAccessManager (.deploydock_accounts.json, sessões, vínculos Git/Google)
│   ├── notification_service.py       # NotificationService (E-mail SMTP HTML, Discord, Slack, Telegram, Webhook)
│   └── paas_service.py               # PaaS Manager (OAuth Device GitHub/Google, templates, backups S3)
```

### Detalhes Técnicos Importantes do Backend
1. **Execução não-bloqueante do Docker SDK:** Como `docker-py` é síncrono, todas as chamadas pesadas em `DockerService` usam `await asyncio.to_thread(...)`.
2. **Coleta de Logs (`DockerService.get_container_logs` e `stream_container_logs`):**
   - Suporta `tail`, `since` (segundos/timestamp) e `timestamps=True/False`.
   - O WebSocket `/api/v1/ws/logs/{container_id}` envia um lote inicial (`initial_tail`) e continua fazendo stream em tempo real via thread daemon + `asyncio.Queue`.
3. **Auto-Detecção de Stack (Nixpacks-like em `DeployOrchestrator._ensure_dockerfile`):**
   - Se o projeto está em modo `dockerfile` mas o repositório não tem `Dockerfile`, o sistema detecta `package.json` (Node.js), `requirements.txt` (Python), `go.mod` (Go) ou `index.html` (Nginx estático) e gera um `Dockerfile` otimizado automaticamente.
4. **Roteamento Traefik (`core/routing.py`):**
   - `build_traefik_labels(project_name, host, internal_port)` cria o roteador HTTP (`web`) e, se `settings.APPS_TLS_ENABLED=True`, cria o roteador HTTPS (`websecure` com `certresolver=letsencrypt`) + middleware de redirect HTTP → HTTPS.
5. **WAF e Segurança (`core/waf.py`):**
   - Singleton `security_engine` em memória com deque de eventos (`max 500`), contadores de rate limit por IP, detecção de ataques por regex e bloqueio temporário automático em caso de brute-force no `/api/v1/auth/login` ou excesso de alertas WAF.
   - Ips locais (`127.0.0.1`, `::1`, `localhost`) nunca são banidos permanentemente para não travar o desenvolvimento local, mas têm seus eventos registrados para auditoria.

---

## 4. Arquitetura Detalhada do Frontend (`frontend/src/`)

```text
frontend/src/
├── assets/main.css                   # Tema Dark Mode customizado + utilitários glassmorphism + scrollbars
├── router/index.ts                   # Rotas + Navigation Guard JWT (redireciona para /login se não autenticado)
├── stores/auth.ts                    # Pinia store para token JWT, dados do usuário logado e logout
├── services/
│   ├── api.ts                        # Cliente Axios tipado para todos os endpoints (/api/v1/*)
│   └── types.ts                      # Interfaces TypeScript (ContainerInfo, Project, Deployment, SystemInfo, etc.)
├── composables/
│   ├── useWebSocket.ts               # Conexão WebSocket com auto-reconnect, backoff exponencial e limpeza
│   ├── useContainerMetrics.ts        # Buffer FIFO de 60 amostras para gráficos de CPU/RAM/Rede em tempo real
│   └── useToast.ts                   # Sistema global de notificações toast
├── components/
│   ├── layout/
│   │   ├── MainLayout.vue            # Layout principal + Gestos Touch Swipe no celular + atalho Ctrl+K
│   │   ├── AppSidebar.vue            # Menu lateral limpo (coluna única, badges ao vivo, colapsável no desktop)
│   │   ├── AppTopbar.vue             # Barra superior com status de CPU/RAM/Disco, contêineres ativos e alertas WAF
│   │   └── CommandPalette.vue        # Modal Ctrl+K de busca global (páginas, contêineres, projetos, ações)
│   ├── containers/
│   │   ├── ContainerTable.vue        # Tabela desktop + Cards mobile para contêineres
│   │   ├── LogViewer.vue             # Visualizador de logs avançado (filtros ERR/WARN/INFO, busca, tail, pause, download)
│   │   └── TerminalExec.vue          # Terminal interativo xterm.js conectado ao WS /ws/exec/{id}
│   ├── projects/
│   │   ├── CreateProjectModal.vue    # Modal de criação de projeto GitOps (Dockerfile, Compose, Auto-detect, Domínio)
│   │   └── ProjectEnvModal.vue       # Editor de variáveis .env do projeto (modo lista e modo texto bruto)
│   └── deployments/
│       └── DeployTimeline.vue        # Histórico de deploys com modal de logs de build e botão de Rollback
└── pages/
    ├── LoginPage.vue                 # Tela de autenticação unificada (Conta Local, GitHub Device, Google Device)
    ├── DashboardPage.vue             # Visão geral de recursos do servidor, contêineres e últimos deploys
    ├── ContainerListPage.vue         # Lista de contêineres + Modal "Quick Launch" (Redis, Postgres, MySQL, Nginx, etc.)
    ├── ContainerDetailPage.vue       # Abas: Visão Geral/Métricas, Logs em Tempo Real, Terminal Web e Explorador de Arquivos
    ├── ProjectsPage.vue              # Gestão de aplicações GitOps, disparo de deploy, rollback, .env e webhook URL
    ├── DeploymentsPage.vue           # Histórico global de todos os deploys
    ├── ResourcesPage.vue             # Gestão de Imagens, Volumes, Redes e botão "System Prune"
    ├── SecurityPage.vue              # Painel do WAF, estatísticas de ataques bloqueados, IPs banidos e logs de ameaças
    ├── SettingsPage.vue              # Checklist de Produção, Gerador de .env, Alterar Senha, Gestão de Usuários e Notificações (SMTP/Webhooks)
    ├── TutorialPage.vue              # Documentação interativa em 6 abas (Configuração, Oracle Cloud, Hostgrid, SSL, Webhooks, WAF)
    ├── AccountPage.vue               # Minha Conta (/account): perfil, vínculo Git/Google, sessões ativas e preferências
    └── AdminAccessPage.vue           # Controle de Acesso (/admin/access): políticas globais OAuth, domínios e revogação de sessões
```

### Detalhes Técnicos Importantes do Frontend
1. **Menu Lateral e Gestos Mobile (`MainLayout.vue` & `AppSidebar.vue`):**
   - No celular (`< 1024px`), o usuário pode **arrastar o dedo da borda esquerda para a direita** para abrir a barra lateral gradualmente acompanhando o toque (`mobileDragTranslateX`), ou arrastar para a esquerda para fechá-la.
   - A barra lateral foi desenhada para ser limpa, sem poluição visual, em coluna única com indicadores claros.
2. **Verificação de Tipos TypeScript:**
   - Sempre validar alterações no frontend rodando:
     ```bash
     cd frontend && npx vue-tsc --noEmit
     ```

---

## 5. Convenções e Regras para Futuras Alterações de IA

1. **Idioma:** Toda a interface do usuário (UI) e respostas ao usuário devem ser em **Português (PT-BR)**.
2. **Não Poluir o Menu Lateral:** Manter `AppSidebar.vue` enxuto em uma única coluna de navegação. Novas ferramentas específicas de contêineres devem entrar como abas em `ContainerDetailPage.vue` ou modais em `ContainerListPage.vue`.
3. **Execução de Comandos no Windows:** Como o ambiente Python/Node/Docker está configurado dentro do WSL (`Ubuntu`), comandos de verificação ou build devem ser executados via `wsl -d Ubuntu -- bash -c "..."` e o reinício do servidor de desenvolvimento via `powershell -ExecutionPolicy Bypass -File .\start-dev.ps1`.
4. **Segurança em Produção:** Nunca expor credenciais reais no `.env.example` ou hardcoded no código. Respeitar o `BACKEND_BIND_IP=127.0.0.1` no `docker-compose.yml` para que o backend em produção seja acessado apenas via proxy Nginx/Traefik.
