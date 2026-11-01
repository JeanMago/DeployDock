# Arquitetura

## 1. Visão geral

```mermaid
flowchart TB
    subgraph Cliente
        B[Navegador - Vue 3 SPA]
        GH[GitHub]
    end

    subgraph Host["Host (VPS / On-Premises)"]
        T[Traefik<br/>proxy reverso + Let's Encrypt]
        subgraph DD[DeployDock]
            F[Frontend Nginx]
            API["Backend FastAPI<br/>WAF · JWT · REST · WebSocket"]
            ORCH[DeployOrchestrator]
            DS[DockerService]
            GS[GitService]
            DB[(PostgreSQL / SQLite)]
        end
        DE[(Docker Engine<br/>docker.sock)]
        APPS[Contêineres das aplicações]
    end

    B -->|HTTPS| T --> F
    B -->|REST + WS| API
    GH -->|webhook HMAC| API
    API --> DB
    API --> ORCH
    ORCH --> GS
    ORCH --> DS --> DE --> APPS
    T -->|labels Docker| APPS
```

### Decisões de projeto

| Decisão | Justificativa | Consequência |
|---|---|---|
| FastAPI assíncrono + SQLAlchemy 2 async | I/O intensivo (Docker, Git, WebSocket) | Baixo consumo e concorrência simples |
| Webhook em vez de *polling* | Latência de deploy menor e sem tráfego ocioso | Exige endpoint público e segredo HMAC |
| Traefik com *labels* dinâmicas | Roteamento/HTTPS sem recarregar configuração | Dependência da rede `deploydock-apps` |
| Estado do WAF em memória | Simplicidade e latência mínima | Executar **1 worker** (ver `backend/Dockerfile`); estado perdido ao reiniciar |
| Docker SDK via `docker.sock` | Controle total sem agente adicional | Superfície de ataque elevada (ver `AMEACAS_E_LIMITACOES.md`) |
| SQLite como *fallback* de desenvolvimento | Subir sem Postgres | Produção deve usar PostgreSQL + `alembic upgrade head` |

## 2. Fluxo do webhook e deploy

```mermaid
sequenceDiagram
    autonumber
    participant GH as GitHub
    participant API as Backend (webhooks.py)
    participant O as DeployOrchestrator
    participant D as Docker Engine
    participant U as Usuário (WebSocket)

    GH->>API: POST /webhooks/github (X-Hub-Signature-256)
    API->>API: valida HMAC (segredo global ou do projeto)
    alt assinatura inválida
        API-->>GH: 401 + evento de auditoria
    else válida
        API-->>GH: 202 Accepted
        API->>O: deploy(project, commit, branch) [background]
        O->>O: clone/pull (token PAT opcional)
        O->>D: build da imagem (stream de logs)
        O-->>U: progresso por WebSocket
        O->>D: para/remove contêiner antigo e inicia o novo
        O->>O: health check (N tentativas)
        alt saudável
            O-->>U: status = healthy
        else falhou
            O->>D: restaura imagem anterior (rollback)
            O-->>U: status = rolled_back
        end
    end
```

## 3. Máquina de estados do deployment

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> cloning
    cloning --> building
    building --> deploying
    deploying --> healthy: health check OK
    cloning --> failed
    building --> failed
    deploying --> failed
    failed --> rolled_back: há imagem anterior
    healthy --> [*]
    failed --> [*]
    rolled_back --> [*]
```

## 4. Modelo de dados

```mermaid
erDiagram
    USER {
        uuid id PK
        string username UK
        string email UK
        string hashed_password
        string role
        bool is_active
    }
    PROJECT ||--o{ DEPLOYMENT : possui
    PROJECT ||--o{ ENVIRONMENT_VARIABLE : define
    PROJECT {
        uuid id PK
        string name UK
        string repo_url
        string branch
        string webhook_secret
        string subdomain UK
        string custom_domain UK
        bool auto_deploy
        string health_check_url
    }
    DEPLOYMENT {
        uuid id PK
        uuid project_id FK
        string commit_sha
        string status
        text build_logs
        string previous_image_id
        float duration_seconds
    }
    ENVIRONMENT_VARIABLE {
        uuid id PK
        uuid project_id FK
        string key
        text value
        bool is_secret
    }
```

## 5. Camadas do WAF / segurança ativa

```mermaid
flowchart LR
    R[Requisição] --> IP{IP bloqueado?}
    IP -- sim --> X1[403]
    IP -- não --> RL{Rate limit?}
    RL -- excedido --> X2[429 / bloqueio]
    RL -- ok --> W{Assinatura WAF?}
    W -- ataque --> X3[403 + auditoria]
    W -- limpa --> A[Autenticação JWT / RBAC]
    A --> H[Handler] --> SH[Security headers na resposta]
```

## 6. Migrações

O esquema é versionado com Alembic (`backend/alembic/`).

```bash
cd backend
alembic upgrade head                       # banco novo
alembic stamp head                         # banco já criado pelo create_all legado
alembic revision --autogenerate -m "msg"   # nova migração após alterar modelos
alembic check                              # falha se modelos e migrações divergirem
```
