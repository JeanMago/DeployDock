# 🐳 DeployDock — Referência Técnica Completa

> **Documento de leitura posterior para retomada de desenvolvimento e embasamento da monografia do TCC.**  
> **Última atualização**: 26/09/2026

---

## 1. Visão Geral do Sistema

O **DeployDock** é uma plataforma auto-hospedável (self-hosted) para gerenciamento de contêineres Docker e entrega contínua (CD) via GitHub Webhooks. O sistema permite que desenvolvedores monitorem, controlem e automatizem deploys de aplicações containerizadas através de uma interface web moderna.

### Problema que resolve

Plataformas de CD existentes (Vercel, Railway, Render) são proprietárias e cobram por uso. O DeployDock oferece uma alternativa gratuita e auto-hospedável que roda em qualquer servidor com Docker, dando ao desenvolvedor controle total sobre a infraestrutura.

### Fluxo principal

```
Developer → git push → GitHub Webhook → DeployDock API → Clone → Build → Deploy → Health Check
                                                                                      ↓
                                                                              Falha? → Rollback automático
```

---

## 2. Arquitetura

### Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Host                                 │
│                                                                     │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐    │
│  │   Frontend    │   │     Backend      │   │   PostgreSQL 16  │    │
│  │   (Nginx)     │──▶│    (FastAPI)     │──▶│                  │    │
│  │   Port 80     │   │    Port 8000     │   │    Port 5432     │    │
│  └──────────────┘   └────────┬─────────┘   └──────────────────┘    │
│                              │                                      │
│                              │ /var/run/docker.sock                 │
│                              ▼                                      │
│                     ┌──────────────────┐                            │
│                     │  Docker Engine   │                            │
│                     │  (containers     │                            │
│                     │   gerenciados)   │                            │
│                     └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Modelo de comunicação

| Origem → Destino              | Protocolo       | Descrição                                    |
|-------------------------------|-----------------|----------------------------------------------|
| Browser → Frontend            | HTTPS           | Servido pelo Nginx (SPA)                     |
| Frontend → Backend (REST)     | HTTP (proxied)  | Nginx faz proxy reverso `/api/*` → `:8000`   |
| Frontend → Backend (realtime) | WebSocket       | Nginx faz proxy `/ws/*` → `:8000` (upgrade)  |
| Backend → PostgreSQL          | TCP (asyncpg)   | Conexão assíncrona via pool                  |
| Backend → Docker Engine       | Unix Socket     | Montagem de `/var/run/docker.sock`           |
| GitHub → Backend              | HTTPS POST      | Webhook com assinatura HMAC-SHA256           |

---

## 3. Stack Tecnológica

### Backend

| Tecnologia               | Versão   | Papel                                             | Por quê?                                                    |
|--------------------------|----------|----------------------------------------------------|-------------------------------------------------------------|
| **Python**               | 3.12+    | Linguagem principal                                | Ecossistema maduro, Docker SDK nativo                       |
| **FastAPI**              | ≥0.115   | Framework web assíncrono                           | Alta performance, tipagem, Swagger automático                |
| **Uvicorn**              | ≥0.30    | Servidor ASGI                                      | Suporte HTTP/2 e WebSocket                                  |
| **SQLAlchemy 2.0**       | ≥2.0.30  | ORM assíncrono                                     | Mapped types, async sessions, migrações via Alembic          |
| **asyncpg**              | ≥0.29    | Driver PostgreSQL nativo                           | Melhor performance async para Postgres                       |
| **docker-py**            | ≥7.1     | SDK Docker para Python                             | API oficial do Docker, operações completas                   |
| **GitPython**            | ≥3.1.43  | Operações Git programáticas                        | Clone/pull sem shell commands                                |
| **Pydantic v2**          | ≥2.7     | Validação de dados e schemas                       | Performance 5-50x vs v1, `from_attributes`                   |
| **httpx**                | ≥0.27    | HTTP client assíncrono                             | Health checks sem bloquear event loop                        |
| **cryptography (Fernet)** | ≥42.0   | Criptografia simétrica                             | Encriptar variáveis de ambiente sensíveis                    |

### Frontend

| Tecnologia               | Versão   | Papel                                             | Por quê?                                                    |
|--------------------------|----------|----------------------------------------------------|-------------------------------------------------------------|
| **Vue.js 3**             | ≥3.5     | Framework SPA (Composition API)                    | Reatividade granular, `<script setup>`, TypeScript nativo     |
| **TypeScript**           | ~5.7     | Tipagem estática                                   | Type-safety entre API e UI                                   |
| **Vite**                 | ≥6.1     | Build tool + dev server                            | HMR instantâneo, ESBuild, tree-shaking                       |
| **Tailwind CSS v4**      | ≥4.0     | Framework CSS utility-first                        | `@theme` direto no CSS, sem `tailwind.config.js`             |
| **vue-router**           | ≥4.4     | SPA routing                                        | Lazy loading de páginas, named routes                        |
| **xterm.js**             | ≥5.5     | Emulador de terminal no browser                    | Renderiza ANSI colors, Canvas de alta performance             |
| **vue-chartjs / Chart.js** | ≥5.3/4.4 | Gráficos de métricas                            | Área charts para CPU/RAM em tempo real                       |
| **Lucide Vue Next**      | ≥0.460   | Ícones SVG                                         | Consistente, leve, tree-shakeable                            |

### Infraestrutura

| Tecnologia         | Papel                                                        |
|--------------------|--------------------------------------------------------------|
| **Docker Compose** | Orquestração dos 3 serviços (backend, frontend, PostgreSQL)  |
| **Nginx**          | Proxy reverso, compressão gzip, SPA fallback, WebSocket proxy |
| **PostgreSQL 16**  | Banco de dados relacional principal                          |

---

## 4. Backend — Detalhamento por Camada

### 4.1. Configuração (`app/core/`)

#### `config.py` — Pydantic Settings
Carrega configuração de variáveis de ambiente e arquivo `.env` seguindo o padrão **12-Factor App**:

```python
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://deploydock:deploydock@localhost:5432/deploydock"
    GITHUB_WEBHOOK_SECRET: str = "changeme"
    SECRET_KEY: str = "changeme-secret-key"
    DOCKER_HOST: str | None = None          # None = usa socket local
    CORS_ORIGINS: list[str] = [...]
    REPOS_BASE_PATH: str = "/app/repos"     # onde repositórios são clonados
    HEALTH_CHECK_TIMEOUT: int = 30          # segundos por tentativa
    HEALTH_CHECK_RETRIES: int = 3           # nº de tentativas
```

> **Nota**: `extra="ignore"` no `SettingsConfigDict` evita crash se houver variáveis extras no `.env`.

#### `security.py` — Segurança

Três responsabilidades:

1. **Validação de Webhooks** — `verify_github_signature(request)`:
   - Lê o body cru do request (`await request.body()`)
   - Calcula `HMAC-SHA256(body, GITHUB_WEBHOOK_SECRET)`
   - Compara com o header `X-Hub-Signature-256` usando `hmac.compare_digest()` (timing-safe)
   - Retorna `bytes` do payload ou `HTTPException(401)`

2. **Criptografia Fernet** — para valores de variáveis de ambiente:
   - `encrypt_value(value: str) -> str` — gera ciphertext base64
   - `decrypt_value(encrypted: str) -> str` — reverte ao plaintext

> **⚠️ Importante**: `hmac.compare_digest()` previne ataques de timing (timing attacks) ao comparar strings em tempo constante.

### 4.2. Banco de Dados (`app/db/`)

#### Conexão e Sessões (`session.py`)

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,        # conexões simultâneas mantidas no pool
    max_overflow=20,     # conexões extras além do pool_size
    pool_pre_ping=True,  # verifica se conexão está viva antes de usar
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,   # evita lazy loading após commit
    autoflush=False,          # controle manual de flush
)
```

A função `get_db()` é uma dependency do FastAPI que gerencia o ciclo de vida da sessão:
- Abre sessão → yield → commit automático
- Se houver exceção → rollback automático

#### Modelos de Dados

**Project** (tabela `projects`):
| Campo              | Tipo            | Descrição                                     |
|--------------------|-----------------|-----------------------------------------------|
| `id`               | UUID (PK)       | Identificador único, gerado automaticamente   |
| `name`             | String (unique) | Nome do projeto                                |
| `repo_url`         | String          | URL do repositório Git (HTTPS)                 |
| `branch`           | String          | Branch monitorada (default: `main`)            |
| `webhook_secret`   | String          | Segredo para validar webhooks deste projeto    |
| `dockerfile_path`  | String          | Caminho do Dockerfile (default: `Dockerfile`)  |
| `auto_deploy`      | Boolean         | Deploy automático ao receber push? (default: true) |
| `health_check_url` | String (null)   | URL para verificar saúde pós-deploy            |
| `created_at`       | DateTime (UTC)  | Data de criação                                |
| `updated_at`       | DateTime (UTC)  | Última atualização                             |

Relacionamentos: `deployments` (1:N), `environment_variables` (1:N) — ambos com `cascade="all, delete-orphan"`.

**Deployment** (tabela `deployments`):
| Campo              | Tipo            | Descrição                                     |
|--------------------|-----------------|-----------------------------------------------|
| `id`               | UUID (PK)       | Identificador único                            |
| `project_id`       | UUID (FK)       | Referência ao projeto                          |
| `commit_sha`       | String(40)      | Hash do commit Git                             |
| `commit_message`   | Text (null)     | Mensagem do commit                             |
| `commit_author`    | String(100)     | Autor do commit                                |
| `branch`           | String(100)     | Branch do deploy                               |
| `status`           | String(20)      | Estado: `pending → cloning → building → deploying → healthy / failed / rolled_back` |
| `build_logs`       | Text (null)     | Saída completa do `docker build`               |
| `error_message`    | Text (null)     | Mensagem de erro (se falhou)                   |
| `previous_image_id`| String(255)     | ID da imagem anterior (para rollback)          |
| `duration_seconds` | Float (null)    | Tempo total do deploy em segundos              |
| `started_at`       | DateTime (UTC)  | Início do deploy                               |
| `finished_at`      | DateTime (UTC)  | Fim do deploy                                  |

**EnvironmentVariable** (tabela `environment_variables`):
| Campo       | Tipo            | Descrição                              |
|-------------|-----------------|----------------------------------------|
| `id`        | UUID (PK)       | Identificador único                     |
| `project_id`| UUID (FK)       | Referência ao projeto                   |
| `key`       | String(255)     | Nome da variável (ex: `DATABASE_URL`)   |
| `value`     | Text            | Valor (encriptado com Fernet)           |
| `is_secret` | Boolean         | Flag indicando se deve ser mascarado    |

### 4.3. Services — Lógica de Negócio (`app/services/`)

#### `DockerService` — Integração com Docker Engine

Wrapper completo do Docker SDK com **20+ métodos**. Padrão central de concorrência:

```
docker-py é SÍNCRONO → asyncio.to_thread() para não bloquear o event loop FastAPI
```

**Operações de Contêiner:**
- `list_containers(all)` → Lista todos com nome, imagem, status, portas
- `get_container(id)` → Detalhes completos (env, mounts, networks)
- `start/stop/restart/remove_container(id)` → Gerenciamento de ciclo de vida
- `get_container_logs(id, tail)` → Últimas N linhas de log
- `stream_container_logs(id)` → Generator síncrono (usado com thread daemon)

**Métricas (CPU/RAM/Rede):**
```python
# Fórmula de CPU% (correta para cgroups):
cpu_delta = current.total_usage - previous.total_usage
system_delta = current.system_cpu_usage - previous.system_cpu_usage
cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

# Memória real (descontando cache inativo):
cache = stats["memory_stats"]["stats"].get("total_inactive_file")
        or stats["memory_stats"]["stats"].get("inactive_file", 0)
memory_used = stats["memory_stats"]["usage"] - cache
```

**Operações de Build e Sistema:**
- `build_image(path, tag, dockerfile)` → Generator que yield linhas de log do build
- `list_images()`, `remove_image(id)` → Gerenciamento de imagens
- `list_volumes()`, `list_networks()` → Inventário
- `get_system_info()` → Versão Docker, contagens de recursos
- `prune_system()` → Limpeza de recursos não utilizados

#### `GitService` — Operações Git

- `clone_repo(url, dest, branch)` → Clona se não existe, ou faz checkout se já existe
- `pull_repo(path, branch)` → Fetch + checkout + pull
- `get_current_commit(path)` → SHA, mensagem, autor, timestamp

> Todos os métodos usam `asyncio.to_thread()` para isolar I/O de disco/rede.

#### `DeployOrchestrator` — Pipeline de Deploy

O coração do sistema. Executa o pipeline completo em 5 etapas:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1. CLONE │───▶│ 2. BUILD │───▶│ 3. SWAP  │───▶│ 4. CHECK │───▶│ 5. DONE  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
                                                      ▼ falha
                                                ┌──────────┐
                                                │ ROLLBACK │
                                                └──────────┘
```

**Detalhes de cada etapa:**

1. **Clone/Pull**: Clona o repositório ou atualiza se já existe. Extrai metadados do commit (SHA, mensagem, autor). Status: `cloning`.

2. **Build**: Constrói a imagem Docker. Utiliza um padrão de bridge entre threads para streaming de logs:
   ```
   [Thread daemon]  →  docker build (bloqueante)
         │                  │
         │ yield linha      │
         ▼                  ▼
   loop.call_soon_threadsafe(queue.put_nowait, linha)
         │
   [Event loop]  ←  await queue.get()
         │
         ▼
   ws_manager.broadcast(topic, log_line)  →  WebSocket clients
   ```
   Este padrão é **crítico** porque o `docker build` é uma operação bloqueante que pode durar minutos.

3. **Swap**: Salva referência à imagem anterior (`previous_image_id`), para o contêiner antigo, remove-o, e inicia o novo com `restart_policy={"Name": "unless-stopped"}`. Status: `deploying`.

4. **Health Check**: Se `project.health_check_url` está configurado, faz requisições HTTP GET com `httpx.AsyncClient` até obter status 200 ou esgotar as tentativas (retry com intervalo de 3s).

5. **Finalização**: Se saudável → status `healthy`. Se falhou → executa rollback automático (reinicia contêiner com imagem anterior) → status `rolled_back`.

> **Rollback manual** também é possível via `POST /api/v1/deployments/{id}/rollback`.

#### `WebSocketManager` — Pub/Sub em Tempo Real

Gerencia conexões WebSocket organizadas por **tópicos**:
- `logs_{container_id}` — streaming de logs
- `metrics_{container_id}` — métricas periódicas
- `deploy_{deployment_id}` — progresso do deploy

```python
active_connections: Dict[str, Set[WebSocket]]
# Exemplo: {"logs_abc123": {ws1, ws2}, "deploy_xyz789": {ws3}}
```

Métodos:
- `connect(ws, topic)` — aceita e registra
- `disconnect(ws, topic)` — remove e limpa tópicos vazios
- `broadcast(topic, message)` — envia para todos no tópico (ignora conexões mortas)
- `send_personal(ws, message)` — envia para um cliente específico

### 4.4. API REST (`app/api/v1/endpoints/`)

#### Tabela de endpoints

| Método   | Rota                                    | Descrição                          |
|----------|-----------------------------------------|------------------------------------|
| `GET`    | `/api/v1/containers`                    | Listar contêineres                 |
| `GET`    | `/api/v1/containers/{id}`               | Detalhes do contêiner              |
| `POST`   | `/api/v1/containers/{id}/start`         | Iniciar contêiner                  |
| `POST`   | `/api/v1/containers/{id}/stop`          | Parar contêiner                    |
| `POST`   | `/api/v1/containers/{id}/restart`       | Reiniciar contêiner                |
| `DELETE` | `/api/v1/containers/{id}`               | Remover contêiner                  |
| `GET`    | `/api/v1/containers/{id}/logs`          | Últimas linhas de log              |
| `GET`    | `/api/v1/projects`                      | Listar projetos                    |
| `POST`   | `/api/v1/projects`                      | Criar projeto                      |
| `GET`    | `/api/v1/projects/{id}`                 | Detalhes do projeto                |
| `PUT`    | `/api/v1/projects/{id}`                 | Atualizar projeto                  |
| `DELETE` | `/api/v1/projects/{id}`                 | Remover projeto                    |
| `POST`   | `/api/v1/projects/{id}/deploy`          | Disparar deploy manual             |
| `GET`    | `/api/v1/projects/{id}/env`             | Listar variáveis de ambiente       |
| `POST`   | `/api/v1/projects/{id}/env`             | Adicionar variável                 |
| `DELETE` | `/api/v1/projects/{id}/env/{env_id}`    | Remover variável                   |
| `GET`    | `/api/v1/deployments`                   | Listar deploys (filtro: project_id)|
| `GET`    | `/api/v1/deployments/{id}`              | Detalhes do deploy (com build logs)|
| `POST`   | `/api/v1/deployments/{id}/rollback`     | Rollback manual                    |
| `POST`   | `/api/v1/webhooks/github`               | Receptor de webhooks GitHub        |
| `GET`    | `/api/v1/system/info`                   | Info do Docker Engine              |
| `GET`    | `/api/v1/system/images`                 | Listar imagens                     |
| `DELETE` | `/api/v1/system/images/{id}`            | Remover imagem                     |
| `GET`    | `/api/v1/system/volumes`                | Listar volumes                     |
| `GET`    | `/api/v1/system/networks`               | Listar redes                       |
| `POST`   | `/api/v1/system/prune`                  | Limpar recursos ociosos            |
| `GET`    | `/health`                               | Health check do backend            |

#### Endpoints WebSocket

| Rota                                        | Descrição                              |
|---------------------------------------------|----------------------------------------|
| `/ws/containers/{id}/logs`                  | Streaming de logs em tempo real         |
| `/ws/containers/{id}/metrics`               | Métricas CPU/RAM a cada 2 segundos     |
| `/ws/deployments/{id}/stream`               | Progresso do pipeline de deploy         |

### 4.5. Webhook do GitHub — Fluxo Detalhado

```
GitHub POST /api/v1/webhooks/github
  │
  ├─ 1. verify_github_signature() → valida HMAC-SHA256
  │     (se inválido → HTTP 401)
  │
  ├─ 2. Verifica X-GitHub-Event header
  │     ├─ "ping" → retorna {"status": "pong"}
  │     └─ "push" → continua
  │
  ├─ 3. Parse do payload JSON
  │     ├─ ref → branch (ex: "refs/heads/main" → "main")
  │     ├─ after → commit_sha
  │     └─ repository.clone_url → repo_url
  │
  ├─ 4. Busca projeto no banco:
  │     WHERE repo_url = ? AND branch = ? AND auto_deploy = true
  │     (se não encontrar → HTTP 200 com "no_matching_project")
  │
  └─ 5. Agenda deploy em background:
        background_tasks.add_task(_trigger_deploy, project_id, commit_sha, branch)
        → Retorna HTTP 202 Accepted imediatamente (não bloqueia o webhook)
        → _trigger_deploy cria sessão DB independente e executa o pipeline
```

> **Por que background task?** O GitHub espera resposta do webhook em até 10 segundos. Um deploy pode levar minutos. Processamos em background e retornamos 202 imediatamente.

---

## 5. Frontend — Detalhamento

### 5.1. Estrutura de diretórios

```
frontend/src/
├── main.ts                        # Bootstrap: createApp + router
├── App.vue                        # Wrapper com <RouterView>
├── assets/
│   └── main.css                   # Tailwind v4 @theme + glass-panel
├── router/
│   └── index.ts                   # 6 rotas com lazy loading
├── services/
│   ├── types.ts                   # Interfaces TypeScript (espelha schemas backend)
│   └── api.ts                     # Cliente HTTP fetch() para /api/v1/*
├── composables/
│   ├── useWebSocket.ts            # WebSocket com auto-reconnect exponencial
│   ├── useContainerMetrics.ts     # Buffer circular de métricas (30 pontos)
│   └── useApi.ts                  # Wrapper genérico de requisições
├── components/
│   ├── layout/
│   │   ├── MainLayout.vue         # Sidebar + Topbar + <RouterView> com transições
│   │   ├── AppSidebar.vue         # Navegação principal com ícones
│   │   └── AppTopbar.vue          # Barra superior com indicadores
│   ├── common/
│   │   ├── StatusBadge.vue        # Badge colorido por status (running/stopped/etc)
│   │   ├── StatCard.vue           # Card de estatística com ícone
│   │   ├── EmptyState.vue         # Estado vazio com ilustração
│   │   └── LoadingSpinner.vue     # Indicador de carregamento
│   ├── containers/
│   │   ├── ContainerCard.vue      # Card de contêiner (grid view)
│   │   ├── ContainerTable.vue     # Tabela de contêineres (list view)
│   │   ├── ContainerActions.vue   # Botões start/stop/restart/remove
│   │   ├── LogViewer.vue          # Terminal xterm.js + WebSocket
│   │   └── MetricsChart.vue       # Gráfico de área CPU/RAM
│   └── deployments/
│       ├── DeployTimeline.vue     # Timeline vertical de histórico
│       └── DeployPipeline.vue     # Stepper horizontal do pipeline
└── pages/
    ├── DashboardPage.vue          # Overview do sistema
    ├── ContainerListPage.vue      # Lista com toggle grid/table
    ├── ContainerDetailPage.vue    # Detalhes + tabs (overview, metrics, logs)
    ├── ProjectsPage.vue           # CRUD de projetos
    ├── DeploymentsPage.vue        # Histórico de deploys
    └── SettingsPage.vue           # Administração do sistema
```

### 5.2. Design System

**Paleta de cores** (definida em `main.css` via `@theme`):

| Token                    | Hex       | Uso                                    |
|--------------------------|-----------|----------------------------------------|
| `--color-dock-bg`        | `#070b14` | Fundo principal (quase preto)          |
| `--color-dock-surface`   | `#0f1629` | Superfícies elevadas                   |
| `--color-dock-panel`     | `#151d30` | Painéis com glassmorphism              |
| `--color-dock-border`    | `#1e2a45` | Bordas sutis                           |
| `--color-dock-text`      | `#e2e8f0` | Texto principal                        |
| `--color-dock-text-muted`| `#94a3b8` | Texto secundário                       |
| `--color-dock-accent`    | `#0ea5e9` | Cor de destaque (sky blue)             |
| `--color-dock-success`   | `#22c55e` | Status positivo (running, healthy)     |
| `--color-dock-warning`   | `#eab308` | Status de atenção (stopped)            |
| `--color-dock-error`     | `#ef4444` | Status de erro (failed)                |
| `--color-dock-info`      | `#6366f1` | Informacional (indigo)                 |

**Tipografia:**
- **UI**: Inter (400, 500, 600, 700) via Google Fonts
- **Código/Logs**: JetBrains Mono (400, 500) via Google Fonts

**Classe `.glass-panel`** (glassmorphism):
```css
.glass-panel {
  @apply bg-dock-panel/80 backdrop-blur-md border border-dock-border shadow-lg rounded-xl;
}
```

### 5.3. Composables — Lógica Reutilizável

#### `useWebSocket(url, onMessage)`
Gerencia conexão WebSocket com **auto-reconnect exponencial**:
- Backoff: `1s → 2s → 4s → 8s → ... → 30s (máximo)`
- Detecta protocolo automaticamente (`http → ws`, `https → wss`)
- Parse JSON automático com fallback para string
- Lifecycle: conecta no `onMounted`, desconecta no `onUnmounted`

#### `useContainerMetrics(containerId)`
Buffer circular de 30 pontos para gráficos em tempo real:
- Conecta via WebSocket em `/ws/containers/{id}/stats`
- Quando `metrics.length > 30`, remove o mais antigo (`shift()`)
- Retorna `{ metrics, status, disconnect }`

### 5.4. Páginas — Funcionalidades

| Página                | Funcionalidades principais                                          |
|-----------------------|---------------------------------------------------------------------|
| **Dashboard**         | 4 StatCards (containers, running, images, memory), tabela dos 5 containers recentes, quick actions |
| **Container List**    | Toggle grid/table view, busca por nome, filtro por status, ações inline (start/stop/restart/remove) |
| **Container Detail**  | 3 tabs: Overview (info + env + mounts), Metrics (gráficos CPU/RAM em tempo real), Logs (xterm.js terminal) |
| **Projects**          | Criar/editar/remover projetos, trigger deploy manual, gerenciar env vars |
| **Deployments**       | Timeline de histórico com status coloridos, detalhes do pipeline, botão de rollback |
| **Settings**          | System info, listagem de images/volumes/networks, botão prune       |

### 5.5. Proxy de Desenvolvimento (Vite)

Em `vite.config.ts`, o dev server na porta 3000 proxeia para o backend na porta 8000:

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': { target: 'http://localhost:8000' },           // REST
    '/ws':  { target: 'ws://localhost:8000', ws: true },   // WebSocket
  }
}
```

Isso elimina problemas de CORS durante desenvolvimento e simula o comportamento do Nginx em produção.

---

## 6. Infraestrutura Docker

### `docker-compose.yml` — Produção

```yaml
services:
  postgres:     # PostgreSQL 16 com volume persistente
  backend:      # FastAPI + Uvicorn, monta docker.sock
  frontend:     # Nginx servindo o build do Vite
```

Detalhes importantes:
- `backend` monta `/var/run/docker.sock:/var/run/docker.sock` para controlar o Docker Engine do host
- `postgres` usa volume nomeado `deploydock_pgdata` para persistência
- `frontend` depende do `backend` e expõe porta 80

### `docker-compose.dev.yml` — Override para desenvolvimento

- Backend: hot reload com volume mount do código fonte
- Frontend: Vite dev server (porta 3000) ao invés do Nginx
- Postgres: porta 5432 exposta para acesso direto com ferramentas como pgAdmin

### Nginx (`frontend/nginx.conf`)

```nginx
upstream backend { server backend:8000; }

location /api/    { proxy_pass http://backend; }
location /ws/     { proxy_pass http://backend; proxy_http_version 1.1;
                    proxy_set_header Upgrade $http_upgrade; ... }
location /health  { proxy_pass http://backend; }
location /        { try_files $uri $uri/ /index.html; }  # SPA fallback
```

- Compressão gzip para JSON, JS, CSS, HTML
- WebSocket upgrade com `Connection: "upgrade"`
- SPA fallback: qualquer rota desconhecida serve `index.html` (vue-router assume)

---

## 7. Padrões de Projeto Utilizados

| Padrão                       | Onde                           | Descrição                                                      |
|------------------------------|--------------------------------|----------------------------------------------------------------|
| **Repository/Service Layer** | `services/`                    | Lógica de negócio isolada dos endpoints                        |
| **Dependency Injection**     | FastAPI `Depends()`            | DockerService e DB session injetados automaticamente            |
| **Pub/Sub**                  | WebSocketManager               | Clientes se inscrevem em tópicos e recebem broadcasts          |
| **Producer-Consumer (Queue)**| Deploy build logs              | Thread produtora → asyncio.Queue → consumer async              |
| **Strategy (Status Machine)**| Deployment.status              | Pipeline muda status sequencialmente: pending→cloning→building→... |
| **Background Task**          | Webhook → deploy               | Deploy assíncrono para não bloquear resposta HTTP              |
| **Singleton**                | `ws_manager`, `settings`       | Instância única compartilhada por toda a aplicação             |
| **Composition API**          | Vue composables                | Lógica reutilizável extraída em funções (`useWebSocket`, etc)  |
| **Sliding Window Buffer**    | `useContainerMetrics`          | Buffer circular de N pontos para gráficos                      |
| **Proxy Pattern**            | Vite dev proxy, Nginx          | Frontend acessa backend sem CORS issues                        |

---

## 8. Segurança

| Aspecto                        | Implementação                                                    |
|--------------------------------|------------------------------------------------------------------|
| Autenticação de Webhooks       | HMAC-SHA256 com `hmac.compare_digest()` (timing-safe)            |
| Criptografia de secrets        | Fernet (AES-128-CBC) para variáveis de ambiente                  |
| CORS                           | Lista de origens permitidas configurável via `.env`              |
| SQL Injection                  | SQLAlchemy ORM com parâmetros vinculados (bind parameters)       |
| Input Validation               | Pydantic v2 valida todos os payloads de entrada                  |
| Docker Socket                  | Acesso via volume mount — ⚠️ dá controle total sobre o host     |

> **⚠️ Atenção**: montar `/var/run/docker.sock` equivale a dar acesso root ao host. Em produção, considerar usar Docker Socket Proxy (como o Tecnativa docker-socket-proxy) para limitar as operações permitidas.

---

## 9. O que Falta Implementar

### Prioridade Alta
- [ ] **Alembic** — migrações de banco de dados (atualmente usa `create_all` que não é incremental)
- [ ] **Primeiro boot funcional** — subir com Docker Compose e validar o fluxo completo end-to-end
- [ ] **Sync frontend ↔ backend** — verificar se campos das interfaces TypeScript batem com os schemas Pydantic

### Prioridade Média  
- [ ] **Testes automatizados** — pytest + pytest-asyncio + httpx para backend
- [ ] **Topbar dinâmica** — valores hardcoded ("12 Running", "CPU: 14%") precisam vir da API
- [ ] **Wiring de botões** — "Deploy New Project", "Trigger Deploy" precisam chamar a API
- [ ] **Gerenciamento de env vars na UI** — modal com inputs para key/value
- [ ] **Notificações toast** — substituir `alert()` / `confirm()` nativos

### Prioridade Baixa
- [ ] **Responsividade mobile** — testar sidebar em telas < 768px
- [ ] **Tema claro (opcional)** — toggle dark/light
- [ ] **Paginação** — endpoints de listagem sem paginação ainda
- [ ] **Rate limiting** — proteção contra abuso dos endpoints

---

## 10. Comandos Úteis para Retomada

```bash
# ── Subir tudo com Docker ──
cp .env.example .env
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# ── Backend local (sem Docker) ──
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs

# ── Frontend local ──
cd frontend
npm install        # node_modules já existe, mas rode se der erro
npm run dev        # http://localhost:3000
npm run build      # verificar se compila sem erros

# ── Verificar TypeScript ──
cd frontend
npx vue-tsc --noEmit

# ── PostgreSQL (necessário para backend local) ──
docker run -d --name deploydock-pg \
  -e POSTGRES_DB=deploydock \
  -e POSTGRES_USER=deploydock \
  -e POSTGRES_PASSWORD=deploydock \
  -p 5432:5432 \
  postgres:16-alpine
```

---

## 11. Referências para a Monografia

| Tema                    | Fontes recomendadas                                              |
|-------------------------|------------------------------------------------------------------|
| Docker Engine API       | https://docs.docker.com/engine/api/                              |
| FastAPI                 | https://fastapi.tiangolo.com/                                    |
| SQLAlchemy 2.0 async    | https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html    |
| GitHub Webhooks         | https://docs.github.com/en/webhooks                              |
| HMAC-SHA256             | RFC 2104 — HMAC: Keyed-Hashing for Message Authentication       |
| Vue.js 3 Composition API| https://vuejs.org/guide/extras/composition-api-faq.html          |
| Tailwind CSS v4         | https://tailwindcss.com/blog/tailwindcss-v4                      |
| WebSocket Protocol      | RFC 6455 — The WebSocket Protocol                                |
| 12-Factor App           | https://12factor.net/                                            |
| GitOps / CD             | Weaveworks GitOps whitepaper                                     |

---

> **Dica**: ao retomar o desenvolvimento, comece subindo o sistema com Docker Compose e verificando se o backend responde em `/health` e o Swagger carrega em `/docs`. Depois teste o frontend acessando `http://localhost:3000` e verifique se a tela do Dashboard carrega.
