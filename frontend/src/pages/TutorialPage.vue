<script setup lang="ts">
import { ref } from 'vue';
import {
  BookOpen,
  Github,
  Terminal,
  Check,
  Copy,
  ArrowRight,
  HelpCircle,
  Sparkles,
  RefreshCw,
  ShieldCheck,
  ExternalLink,
  Globe,
  Server,
  Cloud,
} from 'lucide-vue-next';

const activeTab = ref<'setup' | 'oracle' | 'hostgrid' | 'domains' | 'webhook' | 'pipeline'>('setup');

const copiedKey = ref<string | null>(null);
const currentHost = window.location.origin;
const webhookUrlExample = `${currentHost}/api/v1/webhooks/github`;

const copyCode = (text: string, key: string) => {
  navigator.clipboard.writeText(text);
  copiedKey.value = key;
  setTimeout(() => {
    if (copiedKey.value === key) copiedKey.value = null;
  }, 2000);
};

const oracleInstallScript = `# 1. Atualizar pacotes e instalar Docker + Git na VM Ubuntu da Oracle Cloud
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 2. IMPORTANTE NA ORACLE CLOUD: Liberar portas 80, 443 e 3000 no iptables interno da VM
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 3000 -j ACCEPT
sudo netfilter-persistent save

# 3. Clonar o DeployDock e iniciar o instalador automático de produção
git clone https://github.com/SEU_USUARIO/DeployDock.git
cd DeployDock
chmod +x deploy-prod.sh
sudo ./deploy-prod.sh`;

const hostgridInstallScript = `# 1. Acessar sua VPS Hostgrid via SSH
ssh root@IP_DA_SUA_VPS

# 2. Instalar Docker, Docker Compose e UFW
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh

# 3. Liberar portas no Firewall (SSH, HTTP 80, HTTPS 443)
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp
ufw --force enable

# 4. Clonar o DeployDock e subir em Produção
git clone https://github.com/SEU_USUARIO/DeployDock.git
cd DeployDock
chmod +x deploy-prod.sh
./deploy-prod.sh`;

const envProdSnippet = `# Arquivo .env de Produção (na raiz do projeto DeployDock)
POSTGRES_DB=deploydock
POSTGRES_USER=deploydock
POSTGRES_PASSWORD=SenhaFortePostgres2026!
DATABASE_URL=postgresql+asyncpg://deploydock:SenhaFortePostgres2026!@db:5432/deploydock

SECRET_KEY=gere_uma_chave_hex_de_64_caracteres_aqui
GITHUB_WEBHOOK_SECRET=segredo_global_webhook

# Se tiver domínio próprio: APPS_BASE_DOMAIN=seudominio.com.br e APPS_TLS_ENABLED=true
# Se NÃO tiver domínio (usar apenas IP): APPS_BASE_DOMAIN=SEU_IP_PUBLICO.sslip.io e APPS_TLS_ENABLED=false
APPS_BASE_DOMAIN=seudominio.com.br
DEPLOYDOCK_HOST=painel.seudominio.com.br
APPS_TLS_ENABLED=true
ACME_EMAIL=seu-email@seudominio.com.br
BACKEND_BIND_IP=127.0.0.1

INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=seu-email@seudominio.com.br
INITIAL_ADMIN_PASSWORD=SuaSenhaAdminForte#2026`;

const faqs = ref([
  {
    q: 'Posso subir para produção na Oracle Cloud ou Hostgrid mesmo SEM comprar um domínio?',
    a: 'Sim! O DeployDock suporta nativamente o serviço gratuito sslip.io. Basta configurar APPS_BASE_DOMAIN=SEU_IP_PUBLICO.sslip.io (exemplo: 150.230.10.25.sslip.io) e APPS_TLS_ENABLED=false. Cada projeto que você criar receberá automaticamente um endereço público funcional como http://meuprojeto.150.230.10.25.sslip.io sem precisar configurar DNS!',
  },
  {
    q: 'Por que na Oracle Cloud as portas 80 e 443 às vezes continuam fechadas mesmo após liberar no painel VCN?',
    a: 'As imagens Ubuntu da Oracle Cloud vêm com regras de firewall internas (iptables) que bloqueiam todas as portas exceto a 22 (SSH). Por isso é indispensável rodar os comandos iptables mostrados na aba "Oracle Cloud" (ou rodar nosso script ./deploy-prod.sh, que já faz essa liberação automaticamente).',
  },
  {
    q: 'Como funcionam as variáveis .env dos meus projetos em produção?',
    a: 'Na página Projetos, clique no botão ".env" do card do projeto. Você pode colar todo o seu arquivo .env de uma só vez, marcar variáveis sensíveis como Secret (elas são criptografadas no banco com Fernet AES-128) e clicar em "Aplicar e Reiniciar Container".',
  },
  {
    q: 'Como funciona a proteção contra ataques (WAF e Brute-Force) em produção?',
    a: 'O middleware SecurityShield do DeployDock inspeciona todas as requisições da API contra SQL Injection, XSS, Path Traversal, SSRF em URLs Git e limita tentativas de login (bloqueando automaticamente o IP após 5 falhas consecutivas). Você pode acompanhar tudo em tempo real no menu "Segurança".',
  },
]);

const openFaq = ref<number | null>(0);
const toggleFaq = (idx: number) => {
  openFaq.value = openFaq.value === idx ? null : idx;
};
</script>

<template>
  <div class="space-y-6 max-w-5xl mx-auto pb-12">
    <!-- Cabeçalho -->
    <div class="glass-panel p-5 sm:p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <div>
        <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-dock-accent/15 text-dock-accent text-xs font-mono uppercase mb-2">
          <BookOpen class="w-3.5 h-3.5" /> Documentação Completa & Guia de Produção
        </div>
        <h1 class="text-xl sm:text-2xl font-bold text-dock-text">
          Como Configurar Tudo e Subir para Produção
        </h1>
        <p class="text-xs sm:text-sm text-dock-text-muted mt-1 max-w-2xl">
          Passo a passo completo para configurar projetos, variáveis `.env`, domínios, SSL Let's Encrypt, Webhooks do GitHub e implantar em servidores **Oracle Cloud** ou **Hostgrid**.
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <RouterLink
          to="/settings"
          class="px-3.5 py-2 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-medium text-dock-text transition-colors"
        >
          Gerador de .env
        </RouterLink>
        <RouterLink
          to="/projects"
          class="flex items-center gap-1.5 px-3.5 py-2 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium text-xs transition-colors"
        >
          Ir para Projetos <ArrowRight class="w-3.5 h-3.5" />
        </RouterLink>
      </div>
    </div>

    <!-- Abas do Tutorial -->
    <div class="flex gap-1.5 p-1 glass-panel overflow-x-auto">
      <button
        @click="activeTab = 'setup'"
        class="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'setup'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <Sparkles class="w-3.5 h-3.5 text-dock-accent" /> 1. Configurar Tudo (Passo a Passo)
      </button>

      <button
        @click="activeTab = 'oracle'"
        class="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'oracle'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <Cloud class="w-3.5 h-3.5 text-dock-warning" /> 2. Produção: Oracle Cloud
      </button>

      <button
        @click="activeTab = 'hostgrid'"
        class="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'hostgrid'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <Server class="w-3.5 h-3.5 text-dock-success" /> 3. Produção: Hostgrid VPS
      </button>

      <button
        @click="activeTab = 'domains'"
        class="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'domains'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <Globe class="w-3.5 h-3.5 text-dock-info" /> 4. Domínios, DNS & HTTPS
      </button>

      <button
        @click="activeTab = 'webhook'"
        class="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'webhook'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <Github class="w-3.5 h-3.5 text-dock-accent" /> 5. GitHub Webhook
      </button>

      <button
        @click="activeTab = 'pipeline'"
        class="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'pipeline'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <ShieldCheck class="w-3.5 h-3.5 text-dock-success" /> 6. Segurança & Rollback
      </button>
    </div>

    <!-- ABA 1: COMO CONFIGURAR TUDO -->
    <div v-if="activeTab === 'setup'" class="space-y-5">
      <div class="glass-panel p-5 space-y-5">
        <div>
          <h2 class="text-base font-semibold text-dock-text">
            Fluxo Completo de Configuração do DeployDock
          </h2>
          <p class="text-xs text-dock-text-muted mt-1">
            Siga os 5 passos abaixo para configurar qualquer projeto do zero até a publicação com variáveis `.env`, logs e monitoramento:
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div class="p-4 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="font-mono text-dock-accent font-semibold">PASSO 1 — Criar Projeto ou 1-Click App</div>
            <p class="text-dock-text-muted leading-relaxed">
              Vá em <strong>Projetos → Novo Projeto</strong>. Você pode escolher um <strong>Modelo 1-Click</strong> (FastAPI, Node.js Express, Python Flask, Nginx, Adminer SQL, Status Page) ou clicar em <strong>Repositório Git</strong> e colar o link HTTPS do seu repositório no GitHub/GitLab.
            </p>
          </div>

          <div class="p-4 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="font-mono text-dock-accent font-semibold">PASSO 2 — Configurar Variáveis .env</div>
            <p class="text-dock-text-muted leading-relaxed">
              No card do projeto criado, clique no botão <strong>.env</strong>. Adicione suas chaves (`DATABASE_URL`, `API_KEY`, `PORT`) ou use o <strong>Modo texto .env</strong> para colar múltiplas linhas de uma vez. Marque como <strong>Secret</strong> para criptografar com Fernet AES-128.
            </p>
          </div>

          <div class="p-4 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="font-mono text-dock-accent font-semibold">PASSO 3 — Definir Subdomínio / Porta Interna</div>
            <p class="text-dock-text-muted leading-relaxed">
              Clique no ícone de engrenagem ao lado da URL do projeto para definir o <strong>Subdomínio</strong> (ex: `api.seudominio.com`), um <strong>Domínio Próprio</strong> ou a <strong>Porta Interna do Contêiner</strong> (caso o Dockerfile exponha uma porta específica como `3000` ou `8000`).
            </p>
          </div>

          <div class="p-4 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="font-mono text-dock-accent font-semibold">PASSO 4 — Disparar Deploy e Inspecionar</div>
            <p class="text-dock-text-muted leading-relaxed">
              Clique em <strong>Deploy</strong>. O DeployDock clona o código, constrói a imagem Docker, inicia o contêiner com blindagem `no-new-privileges` e registra a rota no Traefik. Use os botões <strong>Logs</strong>, <strong>Shell</strong> e <strong>Arquivos</strong> para inspecionar tudo ao vivo.
            </p>
          </div>
        </div>

        <!-- Exemplo de .env de Produção -->
        <div class="space-y-2 pt-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono text-dock-text font-semibold">
              Exemplo de arquivo `.env` principal do DeployDock para Produção:
            </span>
            <button
              @click="copyCode(envProdSnippet, 'envProd')"
              class="px-2.5 py-1 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-mono text-dock-text flex items-center gap-1 cursor-pointer"
            >
              <Check v-if="copiedKey === 'envProd'" class="w-3.5 h-3.5 text-dock-success" />
              <Copy v-else class="w-3.5 h-3.5" />
              {{ copiedKey === 'envProd' ? 'Copiado!' : 'Copiar .env' }}
            </button>
          </div>
          <pre class="p-3.5 rounded bg-dock-bg border border-dock-border font-mono text-[11px] text-dock-text overflow-x-auto leading-relaxed">{{ envProdSnippet }}</pre>
        </div>
      </div>
    </div>

    <!-- ABA 2: PRODUÇÃO ORACLE CLOUD -->
    <div v-if="activeTab === 'oracle'" class="space-y-5">
      <div class="glass-panel p-5 space-y-4">
        <div class="border-b border-dock-border pb-3">
          <h2 class="text-base font-semibold text-dock-text flex items-center gap-2">
            <Cloud class="w-5 h-5 text-dock-warning" /> Como Subir em Produção na Oracle Cloud (OCI Free Tier)
          </h2>
          <p class="text-xs text-dock-text-muted mt-1">
            Guia detalhado para instâncias **VM.Standard.A1.Flex (ARM Ampere até 4 OCPUs e 24 GB RAM grátis)** ou **AMD E2.1.Micro** com Ubuntu 22.04 / 24.04 LTS.
          </p>
        </div>

        <div class="space-y-3 text-xs">
          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1.5">
            <div class="font-semibold text-dock-text">1. Criar a Instância e Liberar a VCN Security List (Painel Web da Oracle)</div>
            <ul class="list-disc list-inside text-dock-text-muted space-y-1">
              <li>Acesse <strong>Compute → Instances → Create Instance</strong> e escolha a imagem <strong>Canonical Ubuntu 22.04 ou 24.04</strong>.</li>
              <li>Baixe sua chave SSH privada (`.key`) e anote o <strong>Public IP Address</strong> da VM criada.</li>
              <li>Clique na sua <strong>Subnet → Default Security List → Add Ingress Rules</strong> e adicione 2 regras com Source CIDR `0.0.0.0/0`, protocolo `TCP` e Destination Port Range: <strong>`80`</strong> e <strong>`443`</strong> (e opcionalmente `3000` para acesso direto).</li>
            </ul>
          </div>

          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-dock-text">
                2. Executar os Comandos na VM da Oracle Cloud (SSH)
              </span>
              <button
                @click="copyCode(oracleInstallScript, 'oracle')"
                class="px-2.5 py-1 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-mono text-dock-text flex items-center gap-1 cursor-pointer"
              >
                <Check v-if="copiedKey === 'oracle'" class="w-3.5 h-3.5 text-dock-success" />
                <Copy v-else class="w-3.5 h-3.5" />
                {{ copiedKey === 'oracle' ? 'Copiado!' : 'Copiar Comandos' }}
              </button>
            </div>
            <p class="text-dock-text-dim">
              Conecte-se via `ssh -i sua-chave.key ubuntu@IP_PUBLICO` e execute:
            </p>
            <pre class="p-3 rounded bg-dock-surface border border-dock-border font-mono text-[11px] text-dock-text overflow-x-auto leading-relaxed">{{ oracleInstallScript }}</pre>
          </div>

          <div class="p-3.5 rounded bg-dock-success/10 border border-dock-success/30 text-dock-text">
            <strong>Dica Importante:</strong> O arquivo completo <code class="font-mono text-dock-accent">GUIA_DEPLOY_PRODUCAO_ORACLE_HOSTGRID.md</code> e o instalador automático <code class="font-mono text-dock-accent">deploy-prod.sh</code> já estão salvos na raiz do projeto!
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 3: PRODUÇÃO HOSTGRID VPS -->
    <div v-if="activeTab === 'hostgrid'" class="space-y-5">
      <div class="glass-panel p-5 space-y-4">
        <div class="border-b border-dock-border pb-3">
          <h2 class="text-base font-semibold text-dock-text flex items-center gap-2">
            <Server class="w-5 h-5 text-dock-success" /> Como Subir em Produção pela Hostgrid / VPS Linux
          </h2>
          <p class="text-xs text-dock-text-muted mt-1">
            Passo a passo completo para servidores VPS KVM da Hostgrid (Ubuntu 22.04 / 24.04 ou Debian 12).
          </p>
        </div>

        <div class="space-y-3 text-xs">
          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1.5">
            <div class="font-semibold text-dock-text">1. Preparar a VPS no Painel da Hostgrid</div>
            <ul class="list-disc list-inside text-dock-text-muted space-y-1">
              <li>No painel da Hostgrid, selecione o sistema operacional <strong>Ubuntu 22.04 LTS 64-bit</strong> (ou 24.04 LTS).</li>
              <li>Copie o <strong>Endereço IP Principal</strong> da VPS e a senha `root` enviada no painel/e-mail.</li>
              <li>Recomendado: pelo menos <strong>2 GB de RAM</strong> (ou 1 GB de RAM + 2 GB de Swap criado automaticamente pelo nosso script `deploy-prod.sh`).</li>
            </ul>
          </div>

          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-dock-text">
                2. Instalar Docker, Firewall e Subir o DeployDock na Hostgrid
              </span>
              <button
                @click="copyCode(hostgridInstallScript, 'hostgrid')"
                class="px-2.5 py-1 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-mono text-dock-text flex items-center gap-1 cursor-pointer"
              >
                <Check v-if="copiedKey === 'hostgrid'" class="w-3.5 h-3.5 text-dock-success" />
                <Copy v-else class="w-3.5 h-3.5" />
                {{ copiedKey === 'hostgrid' ? 'Copiado!' : 'Copiar Comandos' }}
              </button>
            </div>
            <pre class="p-3 rounded bg-dock-surface border border-dock-border font-mono text-[11px] text-dock-text overflow-x-auto leading-relaxed">{{ hostgridInstallScript }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 4: DOMÍNIOS, DNS & HTTPS -->
    <div v-if="activeTab === 'domains'" class="space-y-5">
      <div class="glass-panel p-5 space-y-4 text-xs">
        <h2 class="text-base font-semibold text-dock-text border-b border-dock-border pb-3">
          Configurando Domínio Próprio (DNS Wildcard) ou Usando Sem Domínio (`sslip.io`)
        </h2>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-4 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="font-semibold text-dock-accent font-mono">OPÇÃO A — Com Domínio Próprio + HTTPS Automático</div>
            <p class="text-dock-text-muted">
              No painel onde você comprou seu domínio (Registro.br, Cloudflare, Hostgrid, GoDaddy), crie <strong>2 apontamentos DNS do Tipo A</strong> apontando para o IP público da sua VPS:
            </p>
            <div class="p-2.5 rounded bg-dock-surface border border-dock-border font-mono text-[11px] space-y-1">
              <div>Tipo: <strong>A</strong> | Nome: <strong>@</strong> | Destino: <strong>IP_DA_SUA_VPS</strong></div>
              <div>Tipo: <strong>A</strong> | Nome: <strong>*</strong> | Destino: <strong>IP_DA_SUA_VPS</strong></div>
            </div>
            <p class="text-dock-text-dim">
              O registro curinga (<code>*</code>) faz com que qualquer subdomínio (<code>painel.seudominio.com</code>, <code>api.seudominio.com</code>, <code>loja.seudominio.com</code>) chegue automaticamente ao Traefik do DeployDock e receba certificado HTTPS Let's Encrypt!
            </p>
          </div>

          <div class="p-4 rounded bg-dock-bg border border-dock-border space-y-2">
            <div class="font-semibold text-dock-success font-mono">OPÇÃO B — Sem Comprar Domínio (Usando sslip.io)</div>
            <p class="text-dock-text-muted">
              Se você ainda não tem um domínio próprio, basta usar o IP público da sua VPS seguido de <code>.sslip.io</code> no seu arquivo <code>.env</code>:
            </p>
            <div class="p-2.5 rounded bg-dock-surface border border-dock-border font-mono text-[11px] space-y-1">
              <div>APPS_BASE_DOMAIN=<strong>150.230.10.25.sslip.io</strong></div>
              <div>DEPLOYDOCK_HOST=<strong>painel.150.230.10.25.sslip.io</strong></div>
              <div>APPS_TLS_ENABLED=<strong>false</strong></div>
            </div>
            <p class="text-dock-text-dim">
              Todos os projetos que você criar abrirão imediatamente no navegador como <code>http://meu-app.150.230.10.25.sslip.io</code>!
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 5: GITHUB WEBHOOK -->
    <div v-if="activeTab === 'webhook'" class="space-y-5">
      <div class="glass-panel p-5 space-y-5 text-xs">
        <div class="flex items-center justify-between border-b border-dock-border pb-3">
          <div>
            <h2 class="text-base font-semibold text-dock-text flex items-center gap-2">
              <Github class="w-5 h-5 text-dock-accent" /> Configurar Auto-Deploy via GitHub Webhook
            </h2>
            <p class="text-dock-text-muted mt-0.5">
              Sempre que você fizer `git push`, o GitHub avisa o DeployDock, que atualiza a aplicação sem downtime.
            </p>
          </div>
          <a
            href="https://docs.github.com/webhooks"
            target="_blank"
            class="text-dock-accent hover:underline flex items-center gap-1"
          >
            Docs GitHub <ExternalLink class="w-3.5 h-3.5" />
          </a>
        </div>

        <div class="rounded-lg overflow-hidden border border-dock-border bg-black/40 p-3 flex justify-center">
          <img
            src="/github-webhook-guide.png"
            alt="Tela de configuração de Webhooks do GitHub"
            class="rounded max-h-[380px] w-auto border border-dock-border object-contain"
          />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1.5">
            <div class="font-mono text-dock-accent font-semibold">1. Payload URL</div>
            <div class="font-mono text-[11px] bg-dock-surface p-2 rounded border border-dock-border break-all">
              {{ webhookUrlExample }}
            </div>
            <button
              @click="copyCode(webhookUrlExample, 'whUrl')"
              class="text-[11px] font-mono text-dock-accent hover:underline cursor-pointer"
            >
              {{ copiedKey === 'whUrl' ? '✓ URL Copiada!' : 'Copiar Payload URL' }}
            </button>
          </div>

          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1.5">
            <div class="font-mono text-dock-warning font-semibold">2. Content type</div>
            <p class="text-dock-text-muted">
              Selecione obrigatoriamente <code class="font-mono text-dock-text">application/json</code> no seletor do GitHub.
            </p>
          </div>

          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1.5">
            <div class="font-mono text-dock-success font-semibold">3. Secret (HMAC-SHA256)</div>
            <p class="text-dock-text-muted">
              No card do seu projeto em <strong>Projetos → botão .env</strong>, copie o <strong>Webhook Secret</strong> exclusivo do projeto e cole no campo Secret do GitHub.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 6: PIPELINE, ROLLBACK & SEGURANÇA WAF -->
    <div v-if="activeTab === 'pipeline'" class="space-y-5">
      <div class="glass-panel p-5 space-y-4 text-xs">
        <h2 class="text-base font-semibold text-dock-text border-b border-dock-border pb-3">
          Segurança Ativa (WAF), Isolamento de Contêineres & Rollback Automático
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1">
            <div class="font-mono text-dock-accent font-semibold">1. WAF & Rate Limit</div>
            <p class="text-dock-text-muted">
              Bloqueia SQL Injection, XSS, Path Traversal (`../etc/passwd`), SSRF em URLs Git e limita requisições por minuto por IP.
            </p>
          </div>
          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1">
            <div class="font-mono text-dock-warning font-semibold">2. Anti-Brute-Force</div>
            <p class="text-dock-text-muted">
              Após 5 tentativas falhas de login, o endereço IP invasor é automaticamente adicionado à Blocklist do Firewall.
            </p>
          </div>
          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1">
            <div class="font-mono text-dock-success font-semibold">3. Isolamento Docker</div>
            <p class="text-dock-text-muted">
              Contêineres iniciam com `no-new-privileges:true` e `pids_limit=256`, impedindo escalação de privilégio e fork-bombs.
            </p>
          </div>
          <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-1">
            <div class="font-mono text-dock-info font-semibold">4. Rollback Instantâneo</div>
            <p class="text-dock-text-muted">
              Se o novo contêiner falhar, o DeployDock restaura a imagem anterior automaticamente ou com 1 clique na página Deploys.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Perguntas Frequentes -->
    <div class="glass-panel p-5 space-y-3">
      <h2 class="text-sm font-semibold text-dock-text flex items-center gap-2">
        <HelpCircle class="w-4 h-4 text-dock-accent" /> Perguntas Frequentes (FAQ de Produção)
      </h2>

      <div class="space-y-2">
        <div
          v-for="(item, idx) in faqs"
          :key="idx"
          class="rounded border border-dock-border bg-dock-bg overflow-hidden"
        >
          <button
            @click="toggleFaq(idx)"
            class="w-full p-3.5 text-left flex items-center justify-between gap-4 hover:bg-dock-surface transition-colors cursor-pointer"
          >
            <span class="text-xs font-semibold text-dock-text">{{ item.q }}</span>
            <span class="text-xs font-mono text-dock-accent shrink-0">{{ openFaq === idx ? '−' : '+' }}</span>
          </button>
          <div
            v-if="openFaq === idx"
            class="px-3.5 pb-3.5 text-xs text-dock-text-muted leading-relaxed border-t border-dock-border/60 pt-2.5"
          >
            {{ item.a }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
