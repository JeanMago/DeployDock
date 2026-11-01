# 🐳 DeployDock

**Plataforma Auto-Hospedável de Gerenciamento Docker, PaaS e GitOps Simplificado** — Uma alternativa leve, moderna e segura ao Coolify, Portainer e CapRover para gerenciar contêineres, automatizar deploys via GitHub Webhooks, rotear domínios com SSL automático (Traefik + Let's Encrypt) e proteger suas aplicações com WAF integrado.

---

## 📋 Sobre o Projeto

O **DeployDock** unifica em uma única interface responsiva (Desktop & Mobile com gestos touch):

- **Gerenciamento Completo de Contêineres Docker** — Dashboard em tempo real, Quick App Launcher (catálogo 1-clique para Redis, Postgres, MySQL, Nginx, Uptime Kuma, Adminer ou imagem customizada), Terminal Interativo (`/bin/sh` / `/bin/bash`), Explorador de Arquivos dentro do contêiner, e coletor avançado de logs com filtro por severidade (`ERROR`, `WARN`, `INFO`), regex, pausa e download.
- **Deploy Contínuo GitOps (Zero-Config & Dockerfile)** — Pipeline automatizado (`Clone → Build / Nixpacks Auto-Dockerfile → Deploy → Health Check → Rollback`) acionado manualmente ou por eventos `push` do GitHub validados via **HMAC-SHA256**.
- **Roteamento Reverso & HTTPS Automático** — Integração nativa com **Traefik v3** para subdomínios automáticos (`projeto.seudominio.com` ou `projeto.<IP>.sslip.io`), domínios customizados e redirecionamento automático HTTP → HTTPS (Let's Encrypt).
- **Segurança Ativa (WAF + Rate Limiter + Anti-Brute-Force)** — Middleware de inspeção de pacotes contra SQL Injection, XSS, Path Traversal e Command Injection, bloqueio automático de IPs atacantes e painel de auditoria em tempo real.

---

## ✨ Funcionalidades Principais

| Módulo | Funcionalidades |
|---|---|
| 🖥️ **Dashboard & Métricas** | Monitoramento de CPU, RAM, Disco, Rede e I/O em tempo real via WebSockets |
| 📦 **Contêineres & Quick Launch** | Start, Stop, Restart, Remove, lançamento rápido de serviços em 1 clique e inspeção detalhada |
| 📜 **Coleta Avançada de Logs** | Streaming WebSocket com reconexão automática, busca/filtro por nível (`ERR`, `WARN`, `INFO`), seletor de `tail`, tela cheia e exportação `.log` |
| 📁 **File Explorer & Terminal Web** | Navegação de diretórios dentro do contêiner, leitura de arquivos de configuração e terminal interativo `xterm.js` |
| 🚀 **Projetos & GitOps** | Suporte a **Dockerfile**, **Docker Compose** e **Auto-Detecção (Node.js, Python, Go, HTML)**, editor `.env` em lote e Rollback em 1 clique |
| 🛡️ **WAF & Segurança (`/security`)** | Proteção contra SQLi/XSS/Path Traversal, Rate Limiting por IP, proteção Anti-Brute-Force no login, Security Headers (CSP, HSTS, X-Frame-Options) e bloqueio manual/automático de IPs |
| 🧹 **Recursos Docker (`/resources`)** | Gerenciamento de Imagens, Volumes e Redes com **System Prune** (limpeza de cache/imagens órfãs) |
| ⌘ **Command Palette (`Ctrl+K`)** | Busca global rápida de páginas, projetos, contêineres e ações |
| 📱 **UX Desktop & Mobile** | Menu lateral colapsável no computador e gaveta deslizante com suporte a **arrastar o dedo (swipe touch gesture)** no celular |
| ⚙️ **Prontidão de Produção (`/settings`)** | Checklist em tempo real de prontidão para produção, gerador interativo de `.env` (Domínio próprio ou `sslip.io`) e gestão de usuários/senhas |
| 📖 **Tutorial Integrado (`/tutorial`)** | Guia passo a passo dentro do sistema cobrindo `.env`, Oracle Cloud (OCI), Hostgrid VPS, DNS/SSL e Webhooks |

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Docker SDK (`docker-py`) |
| **Segurança** | WAF Middleware · JWT (`PyJWT`) · PBKDF2-HMAC-SHA256 · HMAC-SHA256 Webhook Verification |
| **Frontend** | Vue.js 3 (Composition API) · TypeScript · Tailwind CSS · Pinia · Lucide Icons · Xterm.js |
| **Banco de Dados** | PostgreSQL 16 (Produção) / SQLite (Desenvolvimento rápido) |
| **Proxy & SSL** | Traefik v3 · Let's Encrypt ACME (TLS HTTP Challenge) |
| **Infraestrutura** | Docker Engine & Docker Compose v2 |

---

## 🚀 Como Executar

### 1. Produção Automatizada (Oracle Cloud, Hostgrid ou qualquer VPS Ubuntu/Debian)

O DeployDock inclui o script [`deploy-prod.sh`](./deploy-prod.sh) que instala o Docker, configura 2 GB de Swap se necessário, libera as portas no firewall (`iptables` / `ufw`), gera senhas criptográficas no `.env` e sobe toda a stack:

```bash
git clone https://github.com/SEU-USUARIO/DeployDock.git
cd DeployDock
chmod +x deploy-prod.sh

# Com domínio próprio (HTTPS automático Let's Encrypt):
sudo ./deploy-prod.sh seudominio.com seu-email@seudominio.com

# Ou SEM domínio próprio (usa <IP_PUBLICO>.sslip.io automaticamente):
sudo ./deploy-prod.sh
```

> 📖 **Guia Completo de Produção:** Consulte o arquivo [**GUIA_DEPLOY_PRODUCAO_ORACLE_HOSTGRID.md**](./GUIA_DEPLOY_PRODUCAO_ORACLE_HOSTGRID.md) para o passo a passo detalhado na **Oracle Cloud (OCI Always Free)** e na **Hostgrid VPS**.

---

### 2. Desenvolvimento Rápido (Windows / WSL / Linux)

No Windows (com WSL Ubuntu), basta executar:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1
```

Ou no Linux/macOS:

```bash
chmod +x start-dev.sh
./start-dev.sh
```

- **Frontend (Painel Web):** `http://localhost:3000`
- **Backend (API + Swagger UI):** `http://localhost:8000/docs`

---

## 📁 Estrutura do Projeto

```text
DeployDock/
├── docker-compose.yml                        # Stack de Produção (Traefik, Postgres, Backend, Frontend)
├── docker-compose.dev.yml                    # Override para Desenvolvimento
├── deploy-prod.sh                            # Instalador automatizado para VPS Linux (Oracle/Hostgrid)
├── GUIA_DEPLOY_PRODUCAO_ORACLE_HOSTGRID.md   # Documentação detalhada de deploy em produção
├── CHANGELOG.md                              # Histórico detalhado de todas as evoluções do projeto
├── start-dev.ps1 / start-dev.sh              # Scripts de inicialização rápida em desenvolvimento
│
├── backend/                                  # API FastAPI (Python 3.12)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                           # Inicialização FastAPI, CORS, Admin Seed e WAF Middleware
│       ├── core/
│       │   ├── config.py                     # Variáveis de ambiente e configurações globais
│       │   ├── routing.py                    # Geração dinâmica de labels Traefik (HTTP + HTTPS Redirect)
│       │   ├── security.py                   # Hash PBKDF2-HMAC-SHA256 e tokens JWT
│       │   └── waf.py                        # WAF, Rate Limiter, Anti-Brute-Force e Security Headers
│       ├── models/                           # Modelos ORM (User, Project, Deployment)
│       ├── schemas/                          # Schemas Pydantic
│       ├── services/
│       │   ├── docker_service.py             # Gerenciamento de contêineres, arquivos, exec, prune e stats
│       │   └── deploy_orchestrator.py        # Pipeline de build, auto-Dockerfile, healthcheck e rollback
│       └── api/v1/endpoints/                 # Rotas REST (auth, containers, projects, deployments, security, system, webhooks, ws)
│
└── frontend/                                 # SPA Vue 3 + TypeScript + Tailwind CSS
    ├── Dockerfile                            # Multi-stage build (Dev + Nginx Production)
    ├── nginx.conf                            # Configuração Nginx com proxy WebSocket e API
    └── src/
        ├── components/
        │   ├── common/                       # StatCard, StatusBadge, EmptyState
        │   ├── containers/                   # ContainerTable, LogViewer (coleta avançada de logs)
        │   ├── deployments/                  # DeployTimeline (histórico com logs e rollback)
        │   ├── layout/                       # MainLayout (swipe mobile), AppSidebar, AppTopbar, CommandPalette
        │   └── projects/                     # CreateProjectModal, ProjectEnvModal
        ├── pages/
        │   ├── DashboardPage.vue             # Visão geral e telemetria do host
        │   ├── ContainerListPage.vue         # Lista de contêineres + Quick App Launcher
        │   ├── ContainerDetailPage.vue       # Métricas, Logs, Terminal Web e File Explorer
        │   ├── ProjectsPage.vue              # Gestão de aplicações GitOps, .env e Rollback
        │   ├── ResourcesPage.vue             # Imagens, Volumes, Redes e System Prune
        │   ├── SecurityPage.vue              # Painel WAF, IPs bloqueados e eventos de ataque
        │   ├── SettingsPage.vue              # Checklist de produção, Gerador de .env, Senha e Usuários
        │   └── TutorialPage.vue              # Documentação interativa em 6 abas
        ├── router/                           # Rotas protegidas por autenticação JWT
        └── services/                         # Cliente Axios + Tipagens TypeScript
```

---

## 📄 Licença

Este projeto foi desenvolvido como Trabalho de Conclusão de Curso (TCC) em Ciência da Computação.

Distribuído sob a licença [MIT](./LICENSE).

---

## Testes e Qualidade

```bash
cd backend
pip install -r requirements-dev.txt
pytest --cov=app        # 130+ testes automatizados (≥ 90% de cobertura), sem necessidade de Docker
ruff check app tests    # análise estática
alembic upgrade head    # migrações do banco (alembic check valida coerência com os modelos)
```

O pipeline de CI (`.github/workflows/ci.yml`) executa lint, testes com cobertura, build do frontend e build das
imagens Docker a cada push/PR.

## Documentação Acadêmica

| Documento | Conteúdo |
|---|---|
| [`proposta_tcc.txt`](./proposta_tcc.txt) | Proposta, problema, objetivos |
| [`docs/REQUISITOS.md`](./docs/REQUISITOS.md) | RF/RNF numerados, casos de uso e rastreabilidade para os testes |
| [`docs/ARQUITETURA.md`](./docs/ARQUITETURA.md) | Diagramas (arquitetura, sequência, estados, ER), decisões de projeto, migrações |
| [`docs/AMEACAS_E_LIMITACOES.md`](./docs/AMEACAS_E_LIMITACOES.md) | Modelo de ameaças STRIDE, limitações e trabalhos futuros |
| [`docs/METODOLOGIA_AVALIACAO.md`](./docs/METODOLOGIA_AVALIACAO.md) | Hipóteses, experimentos reprodutíveis, estatística, questionário SUS |
| [`docs/ROTEIRO_BENCHMARK_COMPARATIVO.md`](./docs/ROTEIRO_BENCHMARK_COMPARATIVO.md) | Roteiro passo a passo de comparação empírica (**DeployDock vs Portainer CE vs Coolify v4**) |
| [`docs/TRABALHOS_RELACIONADOS.md`](./docs/TRABALHOS_RELACIONADOS.md) | Fundamentação teórica e comparação com Portainer CE e Coolify v4 |
| [`scripts/bench_deploy_downtime.py`](./scripts/bench_deploy_downtime.py) · [`scripts/bench_multiplatform_compare.py`](./scripts/bench_multiplatform_compare.py) | Benchmarks automatizados de downtime (Recreate vs Blue/Green) e comparação multi-plataforma com IC 95 % |
| [`SECURITY.md`](./SECURITY.md) · [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Política de segurança e guia de contribuição |

## Segurança em Produção

Com `ENVIRONMENT=production` o backend **recusa iniciar** se `SECRET_KEY`, `GITHUB_WEBHOOK_SECRET` ou a senha do
administrador inicial usarem valores padrão. Todos os WebSockets exigem JWT (`?token=`). Veja
[`docs/AMEACAS_E_LIMITACOES.md`](./docs/AMEACAS_E_LIMITACOES.md) para riscos conhecidos (ex.: exposição do `docker.sock`).
