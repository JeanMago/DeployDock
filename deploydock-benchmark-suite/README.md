# 🐳 DeployDock Benchmark & Multi-Platform PaaS Probe

Suite completa de diagnóstico, auditoria End-to-End (E2E), testes de segurança (WAF & Hardening), micro-benchmarks de performance (CPU, RAM, Disco I/O) e **relatório interativo comparativo** entre o **DeployDock** e outros softwares de controle de contêineres Docker (**Portainer CE**, **Coolify v4**, **CapRover**, **Dokploy** e **Docker Engine**).

---

## 🎯 O que este projeto testa?

### 1. Bateria E2E de Todas as Funcionalidades do DeployDock (`deploydock_api_tester.py`)
1. **Autenticação OAuth2/JWT & Sessão** (`POST /api/v1/auth/login`, `GET /api/v1/auth/me`)
2. **Controle de Acesso RBAC Multi-Usuário** (`GET /api/v1/auth/users` — Admin, Developer, Viewer)
3. **Security Headers HTTP** (`X-DeployDock-Shield`, `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`)
4. **WAF — Bloqueio de SQL Injection (SQLi)** (`HTTP 403`)
5. **WAF — Bloqueio de Cross-Site Scripting (XSS)** (`HTTP 403`)
6. **WAF — Bloqueio de Path Traversal / LFI (`../../etc/passwd`)** (`HTTP 403`)
7. **WAF — Bloqueio de Remote Code Execution / Log4Shell (`${jndi:...}`)** (`HTTP 403`)
8. **Auditoria de Ameaças & Bloqueio/Desbloqueio Dinâmico de IP** (`/api/v1/security/block`, `/unblock`, `/overview`)
9. **Telemetria de Hardware do Servidor** (`/api/v1/system/info` — CPU, RAM, Disco, Docker Engine)
10. **Inventário de Recursos Docker** (`/api/v1/system/resources` — Imagens, Volumes, Redes)
11. **Checklist Automatizado de Prontidão para Produção** (`/api/v1/system/production-check`)
12. **Listagem e Inspeção Detalhada de Contêineres** (`/api/v1/containers`)
13. **Coletor Avançado de Logs com Tail, Timestamps & Filtros** (`/api/v1/containers/{id}/logs`)
14. **Execução Remota de Comandos no Terminal Web** (`POST /api/v1/containers/{id}/exec`)
15. **Proteção do Terminal contra Escape via Docker Socket / Fork Bomb** (`HTTP 403`)
16. **Explorador de Arquivos Interno — Listagem de Diretórios** (`GET /api/v1/containers/{id}/files`)
17. **Explorador de Arquivos Interno — Edição e Leitura In-Place** (`PUT & GET /api/v1/containers/{id}/files/content`)
18. **Explorador de Arquivos Interno — Upload Base64, Download Binário & Exclusão** (`/upload`, `/download`, `DELETE /files`)
19. **Roteamento Dinâmico Traefik & Subdomínios** (`/api/v1/projects/routing-config`)
20. **Criação de Projeto GitOps com Quotas de CPU/RAM & Auto-Healing** (`POST /api/v1/projects`)
21. **Cofre de Variáveis `.env` com Criptografia Simétrica Fernet AES-128** (`/api/v1/projects/{id}/env`)
22. **Ambientes de Preview Isolados por Branch / Pull Request** (`/api/v1/projects/{id}/previews`)
23. **Validação Criptográfica de Webhooks GitHub (HMAC-SHA256)** (`POST /api/v1/webhooks/github`)
24. **Monitor de Uptime HTTP, Latência & Auto-Healing** (`/api/v1/projects/uptime/overview`)
25. **Backup & Restore de Volumes Docker em 1 Clique (`.tar.gz`)** (`/api/v1/system/volumes/{name}/restore` e `/backup`)
26. **Motor de Notificações Multicanal (Discord, Slack, Telegram, Webhook)** (`/api/v1/system/notifications/test`)

---

### 2. Sonda Portável de Contêiner & Benchmark (Compatível com Qualquer Gerenciador Docker)
Quando executado dentro de **qualquer** plataforma de controle Docker (**DeployDock**, **Portainer**, **Coolify**, **CapRover**, **Dokploy**):
- **Inspeção de Cgroups v1/v2**: Verifica limites reais de Memória RAM (`memory.max`), vCPUs (`cpu.max`) e limite de processos (`pids.max`).
- **Auditoria de Hardening Linux**: Verifica `NoNewPrivs` (`no-new-privileges`), `Seccomp`, `Capabilities` (`CapEff`), isolamento do `/var/run/docker.sock`.
- **Micro-Benchmarks Sintéticos**: Mede `ops/s` de CPU, taxa de transferência de Memória RAM (`MB/s`) e escrita/leitura de Disco (`MB/s`).
- **Laboratório Interativo**: Permite simular falha no `/health` (`HTTP 500`) para testar Auto-Healing/Rollback, disparar rajadas de logs (`INFO`, `WARN`, `ERROR`) e manipular arquivos em `/app/workspace`.

---

## 🚀 Como Executar

### Opção 1: Executar Auditoria CLI + Gerar Relatório HTML Interativo Impresso
```bash
python3 run_cli_audit.py
```
O relatório interativo completo será salvo em:
- `reports/relatorio_interativo_deploydock.html` (pode ser aberto diretamente no navegador)
- `reports/latest_report.json` (snapshot para comparação)

### Opção 2: Subir o Painel Web Interativo (Porta 8095)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8095
```
Ou via Docker Compose (no DeployDock, Portainer Stacks, Coolify ou terminal):
```bash
docker compose up -d --build
```
Acesse: **`http://localhost:8095`**

---

## 🔄 Como Comparar com Outro Software de Controle Docker (Portainer, Coolify, CapRover, Dokploy)

1. Execute esta aplicação no **DeployDock** e clique em **"📥 Exportar Snapshot (.json)"** (ou use os dados ao vivo).
2. Suba esta mesma pasta/repositório em outro gerenciador Docker (ex: **Portainer**, **Coolify**, **CapRover** ou **Dokploy**) usando o `Dockerfile`, `docker-compose.yml` ou `captain-definition`.
3. Na interface da aplicação rodando no outro software, clique em **"📥 Exportar Snapshot (.json)"**.
4. No relatório interativo, clique em **"📤 Importar de Outro Software"** e selecione o arquivo `.json` exportado — os gráficos de Radar, Barras, Tabela de Performance e Matriz de Funcionalidades serão atualizados instantaneamente lado a lado!
