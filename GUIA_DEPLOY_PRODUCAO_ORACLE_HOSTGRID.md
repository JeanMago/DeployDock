# Guia Completo: Como Subir o DeployDock para Produção (Oracle Cloud & Hostgrid VPS)

Este documento explica **passo a passo, do zero**, como implantar o **DeployDock** em um servidor de produção real utilizando a **Oracle Cloud Infrastructure (OCI Free Tier)** ou uma **VPS da Hostgrid (ou Hostinger/DigitalOcean)**, tanto **com domínio próprio (HTTPS Let's Encrypt)** quanto **sem domínio próprio (usando apenas o IP público via `sslip.io`)**.

---

## Sumário

1. [Arquitetura de Produção do DeployDock](#1-arquitetura-de-produção-do-deploydock)
2. [Opção 1: Subindo na Oracle Cloud (OCI Free Tier — ARM Ampere ou AMD)](#2-opção-1-subindo-na-oracle-cloud-oci-free-tier--arm-ampere-ou-amd)
3. [Opção 2: Subindo na Hostgrid VPS (KVM Linux)](#3-opção-2-subindo-na-hostgrid-vps-kvm-linux)
4. [Configurando Domínio Próprio (DNS Wildcard + HTTPS) vs. Sem Domínio (`sslip.io`)](#4-configurando-domínio-próprio-dns-wildcard--https-vs-sem-domínio-sslipio)
5. [Arquivo `.env` de Produção Explicado Linha por Linha](#5-arquivo-env-de-produção-explicado-linha-por-linha)
6. [Configurando Auto-Deploy com GitHub Webhooks em Produção](#6-configurando-auto-deploy-com-github-webhooks-em-produção)
7. [Comandos Úteis de Manutenção, Logs e Backup em Produção](#7-comandos-úteis-de-manutenção-logs-e-backup-em-produção)

---

## 1. Arquitetura de Produção do DeployDock

Quando você sobe o DeployDock em produção com `docker compose up -d --build`, 4 serviços principais entram em operação:

| Serviço | Container | Porta Exposta | Função em Produção |
| :--- | :--- | :--- | :--- |
| **Traefik v3.6** | `deploydock-traefik` | `80` (HTTP) e `443` (HTTPS) | Proxy reverso dinâmico que roteia cada aplicação criada para seu próprio subdomínio/domínio e emite certificados SSL Let's Encrypt. |
| **Frontend (Nginx)** | `deploydock-frontend` | `3000` (e via Traefik na `80`/`443`) | Serve a interface SPA compilada em Vue 3 e faz proxy reverso seguro de `/api/` e `/ws/` para o backend. |
| **Backend (FastAPI)** | `deploydock-backend` | `127.0.0.1:8000` (Interno) | API protegida com WAF Shield, Rate Limiting, Anti-Brute-Force, Fernet AES-128 e orquestrador Docker/Git. |
| **PostgreSQL 16** | `deploydock-db` | Interno (`5432` na rede Docker) | Banco de dados relacional com volume persistente (`pg_data`). |

---

## 2. Opção 1: Subindo na Oracle Cloud (OCI Free Tier — ARM Ampere ou AMD)

A Oracle Cloud oferece gratuitamente instâncias **VM.Standard.A1.Flex (ARM64 Ampere com até 4 OCPUs e 24 GB de RAM)** ou **VM.Standard.E2.1.Micro (AMD64)**. O DeployDock é 100% compatível com ambas as arquiteturas (`x86_64` e `arm64`).

### Passo 2.1 — Criar a Instância (VM) no Painel da Oracle
1. Acesse o console da Oracle Cloud e vá em **Compute → Instances → Create Instance**.
2. Em **Image and Shape**:
   - **Image**: Escolha **Canonical Ubuntu 22.04 LTS** ou **Ubuntu 24.04 LTS**.
   - **Shape**: Escolha **Ampere (`VM.Standard.A1.Flex`)** com pelo menos **2 OCPUs e 12 GB de RAM** (ou `VM.Standard.E2.1.Micro` se preferir AMD).
3. Em **Networking**, certifique-se de marcar **Assign a public IPv4 address**.
4. Em **Add SSH keys**, clique em **Save Private Key** para baixar o arquivo `.key` no seu computador.
5. Clique em **Create** e anote o **Public IP Address** gerado (exemplo: `150.230.10.25`).

### Passo 2.2 — Liberar as Portas 80, 443 e 3000 no Painel da Oracle (VCN Security List)
Por padrão, a rede virtual da Oracle bloqueia tudo exceto a porta 22 (SSH). Para abrir as portas web:
1. Na página da sua Instance, clique no nome da **Subnet** (em *Primary VNIC*).
2. Clique em **Default Security List for ...**.
3. Clique em **Add Ingress Rules** e adicione a regra abaixo:
   - **Source Type**: `CIDR`
   - **Source CIDR**: `0.0.0.0/0`
   - **IP Protocol**: `TCP`
   - **Destination Port Range**: `80,443,3000`
   - **Description**: `DeployDock HTTP, HTTPS e Painel`
4. Clique em **Add Ingress Rules** para salvar.

### Passo 2.3 — Acessar via SSH e Desbloquear o Firewall Interno (`iptables`) da Ubuntu Oracle
> **ATENÇÃO (Detalhe Crítico da Oracle Cloud):** Mesmo após liberar as portas no painel web da Oracle, a imagem Ubuntu da Oracle vem com regras `iptables` internas que bloqueiam as portas 80 e 443! Os comandos abaixo (e o script `deploy-prod.sh`) resolvem isso automaticamente.

Abra o terminal (PowerShell ou WSL) no seu computador e conecte-se à VM:

```bash
chmod 400 sua-chave-ssh.key
ssh -i sua-chave-ssh.key ubuntu@IP_PUBLICO_DA_ORACLE
```

Dentro da VM da Oracle Cloud, execute:

```bash
# 1. Atualizar o sistema e instalar Git + Docker
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 2. Liberar portas 80, 443 e 3000 no iptables nativo da Oracle Cloud
sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 3000 -j ACCEPT
sudo netfilter-persistent save

# 3. Clonar o repositório do DeployDock
git clone https://github.com/SEU_USUARIO/DeployDock.git
cd DeployDock

# 4. Executar o instalador automático de produção
chmod +x deploy-prod.sh
sudo ./deploy-prod.sh
```

Pronto! Ao final da execução, o script exibirá a URL do seu painel e a senha forte gerada para o usuário `admin`.

---

## 3. Opção 2: Subindo na Hostgrid VPS (KVM Linux)

Se você contratou um servidor VPS na **Hostgrid** (ou Hostinger / DigitalOcean / Contabo / Hetzner):

### Passo 3.1 — Preparar o Sistema Operacional no Painel da Hostgrid
1. Acesse o painel de controle da sua VPS na Hostgrid (Virtualizor / painel do cliente).
2. Instale ou reinstale o sistema operacional **Ubuntu 22.04 LTS 64-bit** ou **Ubuntu 24.04 LTS 64-bit**.
3. Copie o **IP Público da VPS** e a **senha do usuário `root`**.

### Passo 3.2 — Conectar via SSH e Instalar o DeployDock
No seu computador, abra o terminal e conecte-se:

```bash
ssh root@IP_DA_SUA_VPS_HOSTGRID
```

Dentro da VPS da Hostgrid, execute os comandos abaixo:

```bash
# 1. Atualizar pacotes do Ubuntu e instalar Git + curl
apt update && apt upgrade -y
apt install -y git curl ufw openssl

# 2. Configurar o Firewall UFW (Permitir SSH 22, HTTP 80, HTTPS 443 e Porta 3000)
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp
ufw --force enable

# 3. Clonar o repositório do DeployDock
git clone https://github.com/SEU_USUARIO/DeployDock.git
cd DeployDock

# 4. Rodar o script automático de produção (instala Docker, cria Swap de 2GB, gera .env e sobe a stack)
chmod +x deploy-prod.sh
./deploy-prod.sh
```

---

## 4. Configurando Domínio Próprio (DNS Wildcard + HTTPS) vs. Sem Domínio (`sslip.io`)

Você tem **duas formas** de usar o DeployDock em produção:

### Cenário A: Sem Comprar Domínio (Usando o IP da VPS com `sslip.io`)
Se você quer testar ou usar em produção imediatamente sem gastar com domínio:
- O script `deploy-prod.sh` detecta automaticamente o IP da sua VPS (ex: `150.230.10.25`) e configura:
  - `APPS_BASE_DOMAIN=150.230.10.25.sslip.io`
  - `DEPLOYDOCK_HOST=painel.150.230.10.25.sslip.io`
  - `APPS_TLS_ENABLED=false`
- **Como funciona?** O serviço público `sslip.io` resolve automaticamente qualquer endereço terminado em `150.230.10.25.sslip.io` para o IP `150.230.10.25`!
- Assim:
  - O painel do DeployDock abre em: `http://painel.150.230.10.25.sslip.io` (ou `http://150.230.10.25:3000`)
  - Se você criar um projeto chamado `minha-api`, ele abrirá imediatamente em: `http://minha-api.150.230.10.25.sslip.io`!

### Cenário B: Com Domínio Próprio + Certificados HTTPS Let's Encrypt Automáticos
Se você possui um domínio (ex: `meudominio.com.br` no Registro.br, Cloudflare ou Hostgrid):

1. **No painel DNS do seu domínio**, crie **2 registros do Tipo `A`** apontando para o IP público da sua VPS (Oracle ou Hostgrid):

| Tipo | Nome / Host | Valor / Destino | TTL | Explicação |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `@` | `IP_DA_SUA_VPS` | 300 / Auto | Aponta `meudominio.com.br` para a VPS |
| **A** | `*` | `IP_DA_SUA_VPS` | 300 / Auto | **Wildcard (Curinga)**: Aponta qualquer subdomínio (`painel.meudominio.com.br`, `app1.meudominio.com.br`, etc.) automaticamente para a VPS! |

> **Nota para usuários Cloudflare:** Se usar a Cloudflare, deixe a nuvem como **DNS Only (Cinza)** no registro `*`, ou configure o modo SSL/TLS da Cloudflare para **Full**.

2. **Edite o arquivo `.env` na pasta `DeployDock` da VPS** (`nano .env`):

```ini
APPS_BASE_DOMAIN=meudominio.com.br
DEPLOYDOCK_HOST=painel.meudominio.com.br
APPS_TLS_ENABLED=true
ACME_EMAIL=seu-email@meudominio.com.br
CORS_ORIGINS=["https://painel.meudominio.com.br","http://localhost:3000"]
```

3. **Aplique as alterações recriando os contêineres:**

```bash
sudo docker compose up -d
```

O **Traefik v3.6** emitirá automaticamente os certificados HTTPS Let's Encrypt para `https://painel.meudominio.com.br` e para cada novo projeto que você publicar (`https://meuprojeto.meudominio.com.br`), redirecionando todo tráfego HTTP (porta 80) para HTTPS (porta 443)!

---

## 5. Arquivo `.env` de Produção Explicado Linha por Linha

Você também pode gerar este arquivo visualmente dentro do próprio DeployDock acessando o menu **Configurações → Gerador de `.env` para Produção**.

```ini
# --- Banco de Dados PostgreSQL 16 ---
POSTGRES_DB=deploydock
POSTGRES_USER=deploydock
POSTGRES_PASSWORD= ColoqueUmaSenhaForteAqui123!
DATABASE_URL=postgresql+asyncpg://deploydock:ColoqueUmaSenhaForteAqui123!@db:5432/deploydock

# --- Segurança Criptográfica (JWT + Fernet AES-128 para variáveis .env) ---
# Gere com: openssl rand -hex 32
SECRET_KEY=b8f92e1a4c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f
GITHUB_WEBHOOK_SECRET=segredo_padrao_webhooks

# --- Roteamento Traefik & Domínios ---
APPS_BASE_DOMAIN=meudominio.com.br
DEPLOYDOCK_HOST=painel.meudominio.com.br
APPS_TLS_ENABLED=true
ACME_EMAIL=admin@meudominio.com.br
APPS_NETWORK=deploydock-apps

# Impede que a porta 8000 do FastAPI fique exposta diretamente na internet (acesso apenas via Nginx/Traefik)
BACKEND_BIND_IP=127.0.0.1

# --- Origens permitidas no CORS ---
CORS_ORIGINS=["https://painel.meudominio.com.br"]

# --- Conta de Administrador Inicial ---
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@meudominio.com.br
INITIAL_ADMIN_PASSWORD=SenhaAdminSuperForte#2026
```

---

## 6. Configurando Auto-Deploy com GitHub Webhooks em Produção

Com o DeployDock rodando na Oracle Cloud ou Hostgrid:

1. Acesse o painel do DeployDock (`https://painel.meudominio.com.br` ou `http://painel.SEU_IP.sslip.io`).
2. Vá em **Projetos → Novo Projeto → Repositório Git**, informe a URL HTTPS do seu repositório do GitHub e a branch (`main`).
3. No card do projeto criado, clique no botão **`.env`**.
4. Na parte superior do modal, você verá:
   - **Payload URL**: `https://painel.meudominio.com.br/api/v1/webhooks/github`
   - **Webhook Secret**: Código hexadecimal exclusivo daquele projeto.
5. No seu repositório do GitHub, vá em **Settings → Webhooks → Add webhook**:
   - **Payload URL**: Cole a URL copiada.
   - **Content type**: Selecione **`application/json`** (muito importante!).
   - **Secret**: Cole o Webhook Secret do projeto.
   - **Which events?**: *Just the push event*.
   - Clique em **Add webhook**.

A partir desse momento, todo `git push` na branch monitorada disparará automaticamente o build da nova imagem, a injeção das variáveis `.env` criptografadas, o healthcheck e a substituição sem downtime (ou rollback automático em caso de erro)!

---

## 7. Comandos Úteis de Manutenção, Logs e Backup em Produção

```bash
# Ver status de todos os serviços do DeployDock
sudo docker compose ps

# Acompanhar logs em tempo real do Backend e do Traefik
sudo docker compose logs -f backend traefik

# Atualizar o DeployDock após um git pull
git pull
sudo docker compose up -d --build

# Fazer backup completo do banco de dados PostgreSQL
sudo docker exec deploydock-db pg_dump -U deploydock deploydock > backup_deploydock_$(date +%F).sql

# Restaurar um backup do banco de dados PostgreSQL
cat backup_deploydock_2026-10-18.sql | sudo docker exec -i deploydock-db psql -U deploydock -d deploydock
```
