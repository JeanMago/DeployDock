# 📋 Documentação de Alterações e Guia de Subida para o Git (`CHANGELOG.md`)

Este documento registra detalhadamente **todas as funcionalidades, melhorias de arquitetura, segurança, responsividade e automação de produção** implementadas no **DeployDock**, além do passo a passo exato para subir as alterações para o seu repositório Git/GitHub.

---

## 1. Resumo das Evoluções Implementadas

### 📜 1.1. Coleta Avançada de Logs das Aplicações e Deploys
- **Backend ([`containers.py`](backend/app/api/v1/endpoints/containers.py), [`docker_service.py`](backend/app/services/docker_service.py), [`ws.py`](backend/app/api/v1/endpoints/ws.py)):**
  - Suporte aos parâmetros `tail`, `since` e `timestamps` na rota REST `GET /api/v1/containers/{id}/logs`.
  - Stream em tempo real via WebSocket (`/api/v1/ws/logs/{id}`) enviando histórico inicial configurável e reconexão resiliente com backoff exponencial.
  - Histórico completo dos logs de build de cada deploy (`GET /api/v1/deployments/{id}/logs`).
- **Frontend ([`LogViewer.vue`](frontend/src/components/containers/LogViewer.vue), [`DeployTimeline.vue`](frontend/src/components/deployments/DeployTimeline.vue)):**
  - Filtro em tempo real por **severidade** (`ALL`, `ERROR`, `WARN`, `INFO`) com contadores automáticos de ocorrências.
  - Busca por texto/expressão com destaque visual, seletor de quantidade de linhas (`100`, `300`, `500`, `1000`, `2000`), alternância de timestamps, quebra de linha (`word wrap`), modo tela cheia, botão de **Pausar/Retomar** stream, **Copiar** e **Baixar `.log`**.
  - Modal de inspeção de logs de build diretamente na linha do tempo de deploys.

---

### 📱 1.2. Menu Lateral Limpo e Responsividade (Desktop & Gestos Touch no Celular)
- **Menu Lateral Simplificado ([`AppSidebar.vue`](frontend/src/components/layout/AppSidebar.vue)):**
  - Design limpo em coluna única com indicadores ativos em esmeralda, contadores em tempo real (contêineres ativos e alertas do WAF), atalho para busca rápida (`Ctrl+K`), botão de recolher/expandir no Desktop e perfil do usuário com status do motor Docker.
- **Gestos de Arrastar o Dedo no Celular ([`MainLayout.vue`](frontend/src/components/layout/MainLayout.vue)):**
  - Suporte nativo a **Touch Swipe** (e arraste de mouse): arrastar da borda esquerda para a direita abre o menu lateral suavemente acompanhando o dedo (`translate3d`), e arrastar para a esquerda fecha a gaveta.
- **Tabelas e Cards Adaptativos ([`ContainerTable.vue`](frontend/src/components/containers/ContainerTable.vue), [`DashboardPage.vue`](frontend/src/components/pages/DashboardPage.vue), [`ProjectsPage.vue`](frontend/src/pages/ProjectsPage.vue)):**
  - Visão em tabela no computador e cartões responsivos otimizados para toque em telas mobile.

---

### 🛡️ 1.3. Segurança Ativa (WAF, Rate Limiting, Anti-Brute-Force e Hardening)
- **Motor WAF & Rate Limiter ([`waf.py`](backend/app/core/waf.py), [`security.py`](backend/app/api/v1/endpoints/security.py)):**
  - **Inspeção profunda de requisições (WAF):** Detecção e bloqueio de **SQL Injection (SQLi)**, **Cross-Site Scripting (XSS)**, **Path Traversal (`../`)**, **Command Injection** e **Scanner/Bot Recon** (Nikto, SQLMap, Nmap, `.env`, `wp-admin`).
  - **Rate Limiting por IP:** Limite configurável de requisições por minuto com janela deslizante.
  - **Anti-Brute-Force na Autenticação ([`auth.py`](backend/app/api/v1/endpoints/auth.py)):** Bloqueio temporário automático do IP após 5 tentativas falhas de login ou 8 violações de WAF.
  - **Security Headers:** Injeção automática de `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy` e `Content-Security-Policy`.
- **Painel de Segurança ([`SecurityPage.vue`](frontend/src/pages/SecurityPage.vue)):**
  - Monitoramento ao vivo de ameaças mitigadas, lista de IPs bloqueados, bloqueio/desbloqueio manual de IPs e tabela de auditoria de eventos de segurança.

---

### 🚀 1.4. Novas Funcionalidades de Plataformas PaaS (Estilo Coolify / Portainer / CapRover)
1. **Quick App Launcher ([`ContainerListPage.vue`](frontend/src/pages/ContainerListPage.vue)):**
   - Lançamento em 1 clique de serviços prontos (**Redis**, **PostgreSQL**, **MySQL**, **Nginx**, **Uptime Kuma**, **Adminer**) ou qualquer imagem do Docker Hub com portas, variáveis de ambiente e política de restart.
2. **Explorador de Arquivos do Contêiner ([`ContainerDetailPage.vue`](frontend/src/pages/ContainerDetailPage.vue), [`docker_service.py`](backend/app/services/docker_service.py)):**
   - Navegação visual pelas pastas internas de qualquer contêiner em execução e visualização do conteúdo de arquivos de texto/configuração diretamente pelo navegador.
3. **Auto-Detecção de Stack Sem Dockerfile ([`deploy_orchestrator.py`](backend/app/services/deploy_orchestrator.py)):**
   - Caso o repositório Git não possua um `Dockerfile`, o DeployDock detecta automaticamente projetos **Node.js**, **Python**, **Go** ou **HTML Estático** e gera um `Dockerfile` otimizado de produção em tempo de build.
4. **Rollback Instantâneo e Editor `.env` em Lote ([`ProjectsPage.vue`](frontend/src/pages/ProjectsPage.vue), [`ProjectEnvModal.vue`](frontend/src/components/projects/ProjectEnvModal.vue)):**
   - Reversão rápida para commits anteriores e edição de variáveis de ambiente em modo formulário ou texto `.env` bruto.
5. **Gerenciador de Recursos Docker & System Prune ([`ResourcesPage.vue`](frontend/src/pages/ResourcesPage.vue)):**
   - Inspeção e remoção de Imagens, Volumes e Redes Docker, além de botão **Limpar Cache (System Prune)** para recuperar espaço em disco na VPS.
6. **Command Palette Global `Ctrl+K` ([`CommandPalette.vue`](frontend/src/components/layout/CommandPalette.vue)):**
   - Navegação rápida por teclado entre páginas, contêineres, projetos e ações do sistema.

---

### 🌐 1.5. Preparação Completa para Produção (Oracle Cloud & Hostgrid)
- **Checklist de Prontidão & Gerador de `.env` ([`SettingsPage.vue`](frontend/src/pages/SettingsPage.vue), [`system.py`](backend/app/api/v1/endpoints/system.py)):**
  - Endpoint `GET /api/v1/system/production-check` e interface visual que verifica Traefik, PostgreSQL, `SECRET_KEY`, domínio base, HTTPS e Webhook Secret.
  - Gerador interativo de `.env` para produção com suporte a **domínio próprio** ou modo **sem domínio (`<IP>.sslip.io`)**.
  - Troca de senha do administrador e ativação/exclusão de usuários.
- **Traefik HTTPS + Redirect Automático ([`routing.py`](backend/app/core/routing.py), [`docker-compose.yml`](docker-compose.yml)):**
  - Configuração automática de certificados Let's Encrypt (`websecure`) e redirecionamento HTTP → HTTPS na porta `80`.
- **Validação de Webhook Individual por Projeto ([`webhooks.py`](backend/app/api/v1/endpoints/webhooks.py)):**
  - Validação HMAC-SHA256 compatível tanto com o `webhook_secret` exclusivo de cada projeto quanto com o `GITHUB_WEBHOOK_SECRET` global.
- **Tutorial Interativo ([`TutorialPage.vue`](frontend/src/pages/TutorialPage.vue)), Script [`deploy-prod.sh`](deploy-prod.sh) e Guia [`GUIA_DEPLOY_PRODUCAO_ORACLE_HOSTGRID.md`](GUIA_DEPLOY_PRODUCAO_ORACLE_HOSTGRID.md):**
  - Documentação passo a passo e script automatizado para subir em produção na **Oracle Cloud (OCI)** e **Hostgrid VPS**.

---

## 2. Lista de Arquivos Criados e Modificados

### Novos Arquivos Criados
| Arquivo | Descrição |
|---|---|
| `GUIA_DEPLOY_PRODUCAO_ORACLE_HOSTGRID.md` | Guia passo a passo completo para subir em produção na Oracle Cloud e Hostgrid |
| `CHANGELOG.md` | Documentação completa do que foi feito e guia de Git |
| `deploy-prod.sh` | Script automatizado de instalação em produção (Docker, Swap, Firewall, `.env` e Compose) |
| `backend/app/core/waf.py` | Motor WAF, Rate Limiting, Anti-Brute-Force e Security Headers |
| `backend/app/api/v1/endpoints/security.py` | Endpoints REST de monitoramento e controle do WAF / IPs bloqueados |
| `frontend/src/pages/SecurityPage.vue` | Página de Segurança & WAF em tempo real |
| `frontend/src/pages/ResourcesPage.vue` | Página de gerenciamento de Imagens, Volumes, Redes e System Prune |
| `frontend/src/components/layout/CommandPalette.vue` | Busca rápida global (`Ctrl+K`) |
| `frontend/src/components/projects/ProjectEnvModal.vue` | Modal de edição avançada de variáveis `.env` por projeto |

### 🔑 1.6. Autenticação Unificada, OAuth Git (GitHub) & Google SSO com Device Code
- **OAuth 2.0 Device Flow Resiliente ([`auth.py`](backend/app/api/v1/endpoints/auth.py), [`paas_service.py`](backend/app/services/paas_service.py)):**
  - Integração oficial com GitHub Device Flow (`github.com/login/device`) com controle de intervalo e tratamento do rate limit `slow_down`.
  - Integração oficial com **Google Device Flow** (`google.com/device` + endpoint `/api/v1/auth/oauth/google/device/start` e `/poll`) permitindo autenticação e vinculação de conta Google sem necessidade de configurar URLs de callback locais no Google Cloud Console.
  - Validação direta de `Access Token` (`ya29...`) e `ID Token` (`eyJ...`) pelas APIs oficiais (`oauth2.googleapis.com/tokeninfo` e `googleapis.com/oauth2/v3/userinfo`).
  - Suporte a autenticação via **Senha de App do Google (16 caracteres)** com validação STARTTLS direta no `smtp.gmail.com:587`.
  - Sincronização automática do e-mail Google (`jeandemoura2004@gmail.com`) com a conta do usuário no PostgreSQL e canal de notificações.
- **Tela de Minha Conta ([`AccountPage.vue`](frontend/src/pages/AccountPage.vue) em `/account`):**
  - Perfil completo do usuário com foto, e-mail principal, tipo de conta e vínculo com Git (GitHub) e Google.
  - Visualização de sessões ativas (IP, navegador, data/hora) com opção de revogação.
  - Alternância de login da sessão ativa entre credenciais locais, conta GitHub e conta Google.
- **Painel de Controle de Acesso e Contas Logadas ([`AdminAccessPage.vue`](frontend/src/pages/AdminAccessPage.vue) em `/admin/access`):**
  - Gestão centralizada para Administradores definirem políticas globais de acesso: habilitar/desabilitar login local, GitHub ou Google; auto-cadastro OAuth; papéis padrão (`developer`, `viewer`); restrição por domínios de e-mail permitidos.
  - Tabela de controle de usuários com detalhes de contas vinculadas (GitHub/Google) e revogação de sessões em lote ou individual.
- **Tela de Login Multi-Método ([`LoginPage.vue`](frontend/src/pages/LoginPage.vue)):**
  - Três abas de autenticação rápida: **Conta Local** (usuário/senha + 2FA TOTP), **GitHub (Git)** (Device Code em 1 clique ou Token PAT) e **Google** (Device Code em 1 clique ou Senha de App/Token).

---

### 📧 1.7. Central de Notificações Multicanal com Alertas por E-mail (SMTP + HTML)
- **Serviço de Notificações ([`notification_service.py`](backend/app/services/notification_service.py), [`account_service.py`](backend/app/services/account_service.py)):**
  - Implementação completa do canal de **E-mail SMTP** com suporte a STARTTLS / SSL (Gmail, SendGrid, Amazon SES, Mailgun ou servidor próprio).
  - Templates em HTML modernos e responsivos para eventos críticos:
    - Deploys concluídos com sucesso ou com falha/rollback.
    - Ataques e bloqueios mitigados pelo WAF / Anti-Brute-Force.
    - Queda de contêineres e auto-healing.
    - Alertas de alta utilização de CPU ou Memória RAM do host.
  - Roteamento inteligente de destinatários: envio automático para os e-mails das contas conectadas (Google/GitHub) e lista personalizada configurada no painel.
- **Interface de Configuração de Notificações ([`SettingsPage.vue`](frontend/src/pages/SettingsPage.vue)):**
  - Seção interativa com testes em tempo real de envio de e-mail SMTP, Discord, Telegram, Slack e Webhooks customizados.

---

### Arquivos Modificados
| Arquivo | Principais Alterações |
|---|---|
| `README.md` | Documentação atualizada da arquitetura, funcionalidades, novas páginas e deploy |
| `docker-compose.yml` | Hardening da porta do backend (`127.0.0.1`), target `production` no frontend e labels HTTPS Traefik |
| `backend/app/main.py` | Registro do middleware WAF, headers de segurança e seed inicial de administrador |
| `backend/app/core/routing.py` | Redirecionamento automático HTTP → HTTPS no Traefik quando TLS está ativo |
| `backend/app/services/docker_service.py` | Quick run de contêineres, File Explorer (`list_files`, `read_file`), logs com `since`/`timestamps` e System Prune |
| `backend/app/services/deploy_orchestrator.py` | Auto-geração de Dockerfile (Node/Python/Go/Static) e suporte a Rollback |
| `backend/app/services/account_service.py` | Gerenciador de contas, metadados de sessão, vínculos Git/Google e políticas administrativas |
| `backend/app/services/notification_service.py` | Motor de notificações multicanal (E-mail SMTP com HTML, Discord, Slack, Telegram, Webhook) |
| `backend/app/api/v1/endpoints/auth.py` | OAuth Device Flow (GitHub e Google), login multi-método, endpoints de `/account` e `/admin/access` |
| `backend/app/api/v1/endpoints/containers.py` | Rotas para Quick Launch, File Explorer e coleta avançada de logs |
| `backend/app/api/v1/endpoints/deployments.py` | Rotas de logs de deploy e rollback |
| `backend/app/api/v1/endpoints/projects.py` | Rotas de atualização de `.env` e metadados do projeto |
| `backend/app/api/v1/endpoints/system.py` | Métricas de host, recursos Docker, System Prune, `production-check` e config de notificações |
| `backend/app/api/v1/endpoints/webhooks.py` | Normalização de URL do GitHub e validação de `webhook_secret` por projeto |
| `frontend/src/components/layout/AppSidebar.vue` | Menu lateral com links para Minha Conta (`/account`) e Acessos (`/admin/access`) |
| `frontend/src/components/layout/AppTopbar.vue` | Barra superior com atalhos para perfil do usuário e logout |
| `frontend/src/components/layout/MainLayout.vue` | Gestos touch de arrastar o dedo (swipe) no celular para abrir/fechar a barra lateral |
| `frontend/src/components/containers/LogViewer.vue` | Coletor de logs avançado com filtros de nível, busca, pausa, tail e download |
| `frontend/src/pages/AccountPage.vue` | Tela de Minha Conta com vínculos Git/GitHub e Google OAuth Device, sessões e preferências |
| `frontend/src/pages/AdminAccessPage.vue` | Painel de controle de acessos, tipos de conta, políticas OAuth e revogação de sessões |
| `frontend/src/pages/LoginPage.vue` | Autenticação unificada com abas para Conta Local, GitHub (Device) e Google (Device) |
| `frontend/src/pages/ContainerListPage.vue` | Quick App Launcher com templates prontos em 1 clique |
| `frontend/src/pages/ContainerDetailPage.vue` | Aba de Explorador de Arquivos, Terminal Web e Métricas |
| `frontend/src/pages/ProjectsPage.vue` | Botões de Rollback, modal `.env` e logs de build |
| `frontend/src/pages/SettingsPage.vue` | Checklist de produção, Gerador de `.env`, gestão SMTP de e-mail e canais de alerta |
| `frontend/src/pages/TutorialPage.vue` | Tutorial interativo em 6 abas (Configuração, Oracle Cloud, Hostgrid, SSL, Webhooks e WAF) |

---

## 3. Como Subir Tudo para o Git / GitHub

O arquivo [`.gitignore`](.gitignore) já está configurado para **não enviar** arquivos sensíveis ou pesados (`venv/`, `node_modules/`, `.env`, `*.db`, `repos_data/`).

Execute os comandos abaixo no terminal na pasta raiz do projeto:

```bash
# 1. Verifique os arquivos modificados e novos
git status

# 2. Adicione todos os arquivos documentados e implementados ao stage
git add .

# 3. Crie o commit com uma mensagem descritiva padronizada (Conventional Commits)
git commit -m "feat: add WAF security, advanced log viewer, mobile swipe sidebar, quick launcher, file explorer and Oracle/Hostgrid production setup"

# 4. Envie para o repositório remoto no GitHub
git push origin main
```

> 💡 **Dica:** Caso sua branch principal se chame `master`, substitua `git push origin main` por `git push origin master`.
