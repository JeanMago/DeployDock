# 🐳 DeployDock

**Automação de Infraestrutura e GitOps Simplificado** — Plataforma integrada para gerenciamento de contêineres Docker e entrega contínua orientada a eventos do GitHub.

---

## 📋 Sobre

DeployDock é uma plataforma web **auto-hospedável** e **leve** que unifica:

- **Gerenciamento visual de contêineres Docker** — Dashboard completo para monitorar, controlar e inspecionar contêineres, imagens, volumes e redes.
- **Deploy contínuo via GitHub Webhooks** — Automação do ciclo de deploy (clone → build → deploy → health check → rollback) disparada por eventos de push no repositório.

### Funcionalidades Principais

| Funcionalidade | Descrição |
|---|---|
| 🖥️ Dashboard | Visão geral do estado dos contêineres, métricas de CPU/RAM e histórico de deploys |
| 📦 Gerenciamento de Contêineres | Start, stop, restart, remove, logs em tempo real e métricas |
| 🔗 GitHub Webhooks | Receptor validado via HMAC-SHA256 para deploy automatizado |
| 🔄 Deploy Automático | Pipeline: clone → build → deploy → health check |
| ⏪ Rollback Automático | Reversão automática em caso de falha no health check |
| 📊 Métricas em Tempo Real | CPU%, memória e I/O via WebSocket |
| 📜 Logs Streaming | Terminal xterm.js com logs em tempo real |
| 🔒 Segurança | HMAC-SHA256, variáveis de ambiente encriptadas |

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 / FastAPI |
| Frontend | Vue.js 3 / TypeScript / Tailwind CSS v4 |
| Banco de Dados | PostgreSQL 16 |
| Real-time | WebSockets |
| Docker SDK | docker-py |
| Infraestrutura | Docker Compose |

---

## 🚀 Quick Start

### Pré-requisitos

- [Docker](https://www.docker.com/) e [Docker Compose](https://docs.docker.com/compose/) instalados
- [Git](https://git-scm.com/)

### Produção

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/deploydock.git
cd deploydock

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações (especialmente SECRET_KEY e GITHUB_WEBHOOK_SECRET)

# 3. Suba os serviços
docker-compose up -d --build

# 4. Acesse o dashboard
# http://localhost
```

### Desenvolvimento

```bash
# Suba com hot reload (backend + frontend)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Backend: http://localhost:8000 (API + Swagger UI em /docs)
# Frontend: http://localhost:3000 (Vite dev server)
# PostgreSQL: localhost:5432
```

### Desenvolvimento Local (sem Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## 📁 Estrutura do Projeto

```
deploydock/
├── docker-compose.yml          # Orquestração de produção
├── docker-compose.dev.yml      # Override para desenvolvimento
├── .env.example                # Template de variáveis de ambiente
│
├── backend/                    # API FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # Aplicação FastAPI
│       ├── core/               # Configurações e segurança
│       ├── db/                 # Banco de dados (SQLAlchemy)
│       ├── models/             # Modelos ORM
│       ├── schemas/            # DTOs Pydantic
│       ├── services/           # Lógica de negócio
│       └── api/v1/             # Endpoints REST e WebSocket
│
└── frontend/                   # SPA Vue.js
    ├── Dockerfile
    ├── nginx.conf
    └── src/
        ├── components/         # Componentes Vue
        ├── composables/        # Composables (hooks)
        ├── pages/              # Páginas
        ├── router/             # Vue Router
        └── services/           # API client
```

---

## 🔌 Configurando GitHub Webhook

1. No seu repositório GitHub, vá em **Settings → Webhooks → Add webhook**
2. Configure:
   - **Payload URL**: `http://seu-servidor/api/v1/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: O mesmo valor configurado em `GITHUB_WEBHOOK_SECRET` no `.env`
   - **Events**: Selecione "Just the push event"
3. Crie um projeto no DeployDock apontando para o repositório
4. A cada `git push` na branch monitorada, o deploy será disparado automaticamente

---

## 📄 Licença

Este projeto é parte de um Trabalho de Conclusão de Curso (TCC) em Ciência da Computação.

---

## 👤 Autor

Desenvolvido como projeto acadêmico — Bacharelado em Ciência da Computação.
