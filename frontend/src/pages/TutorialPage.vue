<script setup lang="ts">
import { ref } from 'vue';
import { 
  BookOpen, Github, Terminal, Check, Copy, AlertTriangle, ArrowRight, 
  HelpCircle, Sparkles, RefreshCw, ShieldCheck, ExternalLink, Globe
} from 'lucide-vue-next';

const activeTab = ref<'webhook' | 'create' | 'tunnel' | 'pipeline'>('webhook');

const copiedUrl = ref(false);
const copiedJson = ref(false);
const copiedTunnel = ref(false);

const currentHost = window.location.origin;
const webhookUrlExample = `${currentHost}/api/v1/webhooks/github`;

const copyText = (text: string, type: 'url' | 'json' | 'tunnel') => {
  navigator.clipboard.writeText(text);
  if (type === 'url') {
    copiedUrl.value = true;
    setTimeout(() => copiedUrl.value = false, 2000);
  } else if (type === 'json') {
    copiedJson.value = true;
    setTimeout(() => copiedJson.value = false, 2000);
  } else if (type === 'tunnel') {
    copiedTunnel.value = true;
    setTimeout(() => copiedTunnel.value = false, 2000);
  }
};

const faqs = ref([
  {
    q: 'Por que o GitHub retornou erro ou bolinha vermelha no Webhook?',
    a: 'Em 90% dos casos, o erro ocorre porque o Content type foi deixado como "application/x-www-form-urlencoded" em vez de "application/json", ou o GitHub não conseguiu alcançar a Payload URL (por exemplo, localhost não é acessível publicamente sem um túnel como ngrok ou localtunnel).'
  },
  {
    q: 'O que acontece se o Health Check falhar durante um deploy?',
    a: 'O DeployDock possui rollback automático! Se o novo contêiner não responder no endpoint de saúde ou falhar na inicialização, o DeployDock restaura automaticamente a versão anterior da imagem para manter sua aplicação sempre no ar.'
  },
  {
    q: 'Preciso criar pastas ou repositórios antes de cadastrar um projeto?',
    a: 'Não! No DeployDock você pode escolher um "Modelo Pronto" (FastAPI, Node.js, Nginx). O sistema cria a pasta interna, inicializa o Git, cria os arquivos e cuida de tudo automaticamente sem você precisar escolher diretórios locais.'
  },
  {
    q: 'Como o DeployDock valida que o webhook realmente veio do GitHub?',
    a: 'Toda requisição de webhook envia um cabeçalho "X-Hub-Signature-256" gerado com HMAC-SHA256 usando o Secret configurado. O DeployDock valida essa assinatura criptográfica antes de iniciar qualquer operação de deploy.'
  }
]);

const openFaq = ref<number | null>(0);
const toggleFaq = (idx: number) => {
  openFaq.value = openFaq.value === idx ? null : idx;
};
</script>

<template>
  <div class="space-y-8 max-w-5xl mx-auto pb-12">
    <!-- Cabeçalho do Tutorial -->
    <div class="glass-panel p-6 sm:p-8 relative overflow-hidden">
      <div class="absolute -right-10 -bottom-10 w-64 h-64 bg-dock-accent/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-dock-accent/10 text-dock-accent text-xs font-semibold uppercase tracking-wider mb-3">
            <BookOpen class="w-3.5 h-3.5" /> Central de Ajuda & Guia Prático
          </div>
          <h1 class="text-2xl sm:text-3xl font-bold text-dock-text">Como Usar o DeployDock & GitOps</h1>
          <p class="text-sm text-dock-text-muted mt-2 max-w-2xl leading-relaxed">
            Aprenda a conectar repositórios do GitHub, configurar webhooks passo a passo, criar aplicações prontas e automatizar seu ciclo de entrega contínua.
          </p>
        </div>
        <RouterLink 
          to="/projects"
          class="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-dock-accent hover:bg-dock-accent-hover text-white font-medium text-sm transition-all shadow-lg shadow-dock-accent/20"
        >
          Ir para Projetos <ArrowRight class="w-4 h-4" />
        </RouterLink>
      </div>
    </div>

    <!-- Seletor de Abas do Guia -->
    <div class="flex gap-2 p-1.5 glass-panel rounded-xl overflow-x-auto">
      <button 
        @click="activeTab = 'webhook'" 
        class="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap cursor-pointer"
        :class="activeTab === 'webhook' ? 'bg-dock-surface text-dock-text shadow-sm ring-1 ring-dock-border' : 'text-dock-text-muted hover:text-dock-text'"
      >
        <Github class="w-4 h-4 text-dock-accent" /> Configurar GitHub Webhook
      </button>

      <button 
        @click="activeTab = 'create'" 
        class="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap cursor-pointer"
        :class="activeTab === 'create' ? 'bg-dock-surface text-dock-text shadow-sm ring-1 ring-dock-border' : 'text-dock-text-muted hover:text-dock-text'"
      >
        <Sparkles class="w-4 h-4 text-dock-warning" /> Criar Projetos sem Complicação
      </button>

      <button 
        @click="activeTab = 'tunnel'" 
        class="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap cursor-pointer"
        :class="activeTab === 'tunnel' ? 'bg-dock-surface text-dock-text shadow-sm ring-1 ring-dock-border' : 'text-dock-text-muted hover:text-dock-text'"
      >
        <Globe class="w-4 h-4 text-dock-info" /> Testar Localmente (ngrok / Túnel)
      </button>

      <button 
        @click="activeTab = 'pipeline'" 
        class="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap cursor-pointer"
        :class="activeTab === 'pipeline' ? 'bg-dock-surface text-dock-text shadow-sm ring-1 ring-dock-border' : 'text-dock-text-muted hover:text-dock-text'"
      >
        <RefreshCw class="w-4 h-4 text-dock-success" /> Pipeline & Rollback
      </button>
    </div>

    <!-- ABA 1: CONFIGURAR GITHUB WEBHOOK (PASSO A PASSO COM O PRINT) -->
    <div v-if="activeTab === 'webhook'" class="space-y-6">
      <div class="glass-panel p-6 sm:p-8 space-y-6">
        <div>
          <h2 class="text-xl font-bold text-dock-text flex items-center gap-2.5">
            <Github class="w-6 h-6 text-dock-accent" /> Passo a Passo: Tela "Add Webhook" do GitHub
          </h2>
          <p class="text-sm text-dock-text-muted mt-1">
            Siga as instruções abaixo para preencher exatamente os campos da página de Webhooks do seu repositório no GitHub.
          </p>
        </div>

        <!-- Banner com a imagem enviada pelo usuário -->
        <div class="rounded-xl overflow-hidden border border-dock-border shadow-xl bg-[#0d1117]">
          <div class="p-3 bg-dock-surface/80 border-b border-dock-border flex items-center justify-between">
            <div class="flex items-center gap-2 text-xs font-mono text-dock-text-muted">
              <span class="w-2.5 h-2.5 rounded-full bg-dock-error/70"></span>
              <span class="w-2.5 h-2.5 rounded-full bg-dock-warning/70"></span>
              <span class="w-2.5 h-2.5 rounded-full bg-dock-success/70"></span>
              <span class="ml-2 text-dock-text">Referência Visual: Tela de Webhooks do GitHub</span>
            </div>
            <a 
              href="https://docs.github.com/webhooks" 
              target="_blank" 
              class="text-xs text-dock-accent hover:underline flex items-center gap-1"
            >
              Doc GitHub <ExternalLink class="w-3 h-3" />
            </a>
          </div>
          <div class="p-2 sm:p-4 bg-black/40 flex justify-center">
            <img 
              src="/github-webhook-guide.png" 
              alt="Tela de configuração de Webhooks do GitHub" 
              class="rounded-lg max-h-[480px] w-auto border border-dock-border object-contain shadow-lg"
            />
          </div>
        </div>

        <!-- Tabela detalhada de cada campo do formulário -->
        <div class="space-y-4">
          <h3 class="text-base font-semibold text-dock-text">O que preencher em cada campo:</h3>

          <!-- Campo 1: Payload URL -->
          <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-2">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-6 h-6 rounded-full bg-dock-accent/20 text-dock-accent font-bold text-xs flex items-center justify-center">1</span>
                <span class="font-bold text-sm text-dock-text">Payload URL *</span>
              </div>
              <button 
                @click="copyText(webhookUrlExample, 'url')"
                class="text-xs text-dock-accent hover:underline flex items-center gap-1 cursor-pointer"
              >
                <Check v-if="copiedUrl" class="w-3.5 h-3.5 text-dock-success" />
                <Copy v-else class="w-3.5 h-3.5" />
                {{ copiedUrl ? 'Copiado!' : 'Copiar URL' }}
              </button>
            </div>
            <p class="text-xs text-dock-text-dim">
              O endereço público do seu servidor DeployDock que receberá as notificações do GitHub.
            </p>
            <div class="p-2.5 bg-dock-bg rounded-lg border border-dock-border font-mono text-xs text-dock-accent flex items-center justify-between select-all">
              <span>{{ webhookUrlExample }}</span>
            </div>
            <p class="text-[11px] text-dock-text-dim">
              💡 <em>Se estiver testando na sua máquina local, utilize um túnel (veja a aba "Testar Localmente"). Em produção, use o IP ou domínio do seu servidor.</em>
            </p>
          </div>

          <!-- Campo 2: Content type (ATENÇÃO CRÍTICA) -->
          <div class="p-4 rounded-xl bg-dock-warning/10 border border-dock-warning/30 space-y-2">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-dock-warning/20 text-dock-warning font-bold text-xs flex items-center justify-center">2</span>
              <span class="font-bold text-sm text-dock-warning flex items-center gap-1.5">
                Content type * <AlertTriangle class="w-4 h-4" /> (Atenção!)
              </span>
            </div>
            <p class="text-xs text-dock-text">
              <strong>MUDE para:</strong> <code class="px-2 py-0.5 rounded bg-dock-bg border border-dock-border text-dock-accent font-bold font-mono">application/json</code>
            </p>
            <div class="p-3 rounded-lg bg-dock-bg/80 border border-dock-warning/20 text-xs text-dock-text-muted leading-relaxed">
              ⚠️ <strong>Cuidado:</strong> Por padrão, o GitHub vem selecionado com <code>application/x-www-form-urlencoded</code>. <strong>Você DEVE alterar para <code>application/json</code></strong>, caso contrário o DeployDock não conseguirá ler o payload do push!
            </div>
          </div>

          <!-- Campo 3: Secret -->
          <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-2">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-dock-accent/20 text-dock-accent font-bold text-xs flex items-center justify-center">3</span>
              <span class="font-bold text-sm text-dock-text">Secret</span>
            </div>
            <p class="text-xs text-dock-text-dim">
              O segredo alfanumérico gerado pelo DeployDock para o seu projeto. Ele é usado para assinar e validar com HMAC-SHA256 cada evento de push.
            </p>
            <p class="text-xs text-dock-text-muted">
              Você encontra esse segredo ao criar o projeto ou nas configurações do projeto na aba <strong>Projetos</strong>.
            </p>
          </div>

          <!-- Campo 4: SSL verification -->
          <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-2">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-dock-accent/20 text-dock-accent font-bold text-xs flex items-center justify-center">4</span>
              <span class="font-bold text-sm text-dock-text">SSL verification</span>
            </div>
            <p class="text-xs text-dock-text-dim">
              • Selecione <strong>Enable SSL verification</strong> se sua URL usa HTTPS com certificado válido.<br>
              • Selecione <strong>Disable</strong> apenas temporariamente se estiver testando com HTTP simples em ambiente de testes.
            </p>
          </div>

          <!-- Campo 5: Which events -->
          <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-2">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-dock-accent/20 text-dock-accent font-bold text-xs flex items-center justify-center">5</span>
              <span class="font-bold text-sm text-dock-text">Which events would you like to trigger this webhook?</span>
            </div>
            <p class="text-xs text-dock-text-dim">
              Mantenha selecionado: <strong>Just the push event.</strong> (O deploy será disparado toda vez que alguém fizer <code>git push</code> na branch monitorada).
            </p>
          </div>

          <!-- Campo 6: Active -->
          <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-2">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-dock-accent/20 text-dock-accent font-bold text-xs flex items-center justify-center">6</span>
              <span class="font-bold text-sm text-dock-text">Active (Checkbox)</span>
            </div>
            <p class="text-xs text-dock-text-dim">
              Deixe marcado como <strong>Active</strong> e clique no botão verde <strong>Add webhook</strong> no final da página do GitHub!
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 2: CRIAR PROJETOS DIRETAMENTE -->
    <div v-else-if="activeTab === 'create'" class="space-y-6">
      <div class="glass-panel p-6 sm:p-8 space-y-6">
        <div>
          <h2 class="text-xl font-bold text-dock-text flex items-center gap-2.5">
            <Sparkles class="w-6 h-6 text-dock-warning" /> Adicionando Projetos Diretamente
          </h2>
          <p class="text-sm text-dock-text-muted mt-1">
            Você não precisa se preocupar com onde os arquivos ficam salvos na sua máquina! O DeployDock automatiza todo o processo.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="p-5 rounded-xl bg-dock-surface/40 border border-dock-border space-y-3">
            <div class="w-10 h-10 rounded-lg bg-dock-accent/20 text-dock-accent flex items-center justify-center font-bold">1</div>
            <h3 class="font-bold text-base text-dock-text">Modelos Prontos (Instantâneo)</h3>
            <p class="text-xs text-dock-text-muted leading-relaxed">
              Ideal para iniciar rapidamente. Escolha entre <strong>Python FastAPI</strong>, <strong>Node.js Express</strong>, <strong>Site Estático Nginx</strong> ou um <strong>Dockerfile Customizado</strong>.
            </p>
            <ul class="text-xs text-dock-text-dim space-y-1.5 list-disc list-inside">
              <li>DeployDock cria a pasta interna automaticamente.</li>
              <li>Inicializa o repositório Git local.</li>
              <li>Cria o primeiro commit e executa o build.</li>
            </ul>
          </div>

          <div class="p-5 rounded-xl bg-dock-surface/40 border border-dock-border space-y-3">
            <div class="w-10 h-10 rounded-lg bg-dock-success/20 text-dock-success flex items-center justify-center font-bold">2</div>
            <h3 class="font-bold text-base text-dock-text">Repositório Git Existente</h3>
            <p class="text-xs text-dock-text-muted leading-relaxed">
              Cole a URL do seu repositório no GitHub ou GitLab (ex: <code>https://github.com/usuario/meu-repo</code>).
            </p>
            <ul class="text-xs text-dock-text-dim space-y-1.5 list-disc list-inside">
              <li>O DeployDock clona a branch especificada (ex: <code>main</code>).</li>
              <li>Detecta o <code>Dockerfile</code> ou <code>docker-compose.yml</code>.</li>
              <li>Fica escutando os pushes através do Webhook configurado.</li>
            </ul>
          </div>
        </div>

        <div class="p-4 rounded-xl bg-dock-accent/10 border border-dock-accent/20 flex items-center justify-between">
          <div class="text-xs text-dock-text">
            <strong>Pronto para criar seu primeiro projeto?</strong> Vá para a tela de projetos e clique em "+ Novo Projeto".
          </div>
          <RouterLink 
            to="/projects"
            class="px-3.5 py-1.5 rounded-lg bg-dock-accent hover:bg-dock-accent-hover text-white text-xs font-semibold shrink-0"
          >
            Abrir Projetos
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- ABA 3: TESTAR LOCALMENTE (TUNNEL) -->
    <div v-else-if="activeTab === 'tunnel'" class="space-y-6">
      <div class="glass-panel p-6 sm:p-8 space-y-6">
        <div>
          <h2 class="text-xl font-bold text-dock-text flex items-center gap-2.5">
            <Globe class="w-6 h-6 text-dock-info" /> Como Testar Webhooks na Máquina Local (localhost)
          </h2>
          <p class="text-sm text-dock-text-muted mt-1">
            Como o GitHub está na internet e sua máquina está em <code>localhost</code>, o GitHub precisa de um endereço público para enviar o webhook.
          </p>
        </div>

        <div class="space-y-4">
          <div class="p-4 rounded-xl bg-dock-surface/50 border border-dock-border space-y-3">
            <h3 class="font-semibold text-sm text-dock-text flex items-center gap-2">
              <Terminal class="w-4 h-4 text-dock-accent" /> Opção 1: Usando Localtunnel (Zero Instalação)
            </h3>
            <p class="text-xs text-dock-text-muted">
              Você já tem o Node.js instalado na máquina! Basta abrir um terminal e rodar:
            </p>
            <div class="p-3 bg-dock-bg rounded-lg border border-dock-border font-mono text-xs text-dock-accent flex items-center justify-between select-all">
              <span>npx localtunnel --port 8000</span>
              <button 
                @click="copyText('npx localtunnel --port 8000', 'tunnel')" 
                class="text-dock-text-dim hover:text-dock-text"
              >
                <Check v-if="copiedTunnel" class="w-3.5 h-3.5 text-dock-success" />
                <Copy v-else class="w-3.5 h-3.5" />
              </button>
            </div>
            <p class="text-xs text-dock-text-dim">
              O Localtunnel gerará uma URL pública (ex: <code>https://dry-frog-12.loca.lt</code>). Sua <strong>Payload URL</strong> no GitHub será:<br>
              <code class="text-dock-accent">https://dry-frog-12.loca.lt/api/v1/webhooks/github</code>
            </p>
          </div>

          <div class="p-4 rounded-xl bg-dock-surface/50 border border-dock-border space-y-3">
            <h3 class="font-semibold text-sm text-dock-text flex items-center gap-2">
              <Globe class="w-4 h-4 text-dock-info" /> Opção 2: Usando ngrok
            </h3>
            <p class="text-xs text-dock-text-muted">
              Se tiver o ngrok instalado, basta executar:
            </p>
            <div class="p-3 bg-dock-bg rounded-lg border border-dock-border font-mono text-xs text-dock-text-muted select-all">
              ngrok http 8000
            </div>
            <p class="text-xs text-dock-text-dim">
              Copie a URL HTTPS gerada pelo ngrok e acrescente <code>/api/v1/webhooks/github</code> para colar no GitHub!
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 4: PIPELINE & ROLLBACK -->
    <div v-else-if="activeTab === 'pipeline'" class="space-y-6">
      <div class="glass-panel p-6 sm:p-8 space-y-6">
        <div>
          <h2 class="text-xl font-bold text-dock-text flex items-center gap-2.5">
            <RefreshCw class="w-6 h-6 text-dock-success" /> O Pipeline de Deploy & Rollback Automático
          </h2>
          <p class="text-sm text-dock-text-muted mt-1">
            Entenda o que acontece a cada `git push` no repositório monitorado.
          </p>
        </div>

        <div class="space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-5 gap-3">
            <div class="p-3.5 rounded-xl bg-dock-surface/40 border border-dock-border text-center space-y-1">
              <div class="font-bold text-xs text-dock-accent">Etapa 1</div>
              <div class="font-semibold text-sm text-dock-text">Webhook</div>
              <p class="text-[11px] text-dock-text-dim">Validação HMAC do push</p>
            </div>
            <div class="p-3.5 rounded-xl bg-dock-surface/40 border border-dock-border text-center space-y-1">
              <div class="font-bold text-xs text-dock-accent">Etapa 2</div>
              <div class="font-semibold text-sm text-dock-text">Clone / Pull</div>
              <p class="text-[11px] text-dock-text-dim">Baixa código mais recente</p>
            </div>
            <div class="p-3.5 rounded-xl bg-dock-surface/40 border border-dock-border text-center space-y-1">
              <div class="font-bold text-xs text-dock-accent">Etapa 3</div>
              <div class="font-semibold text-sm text-dock-text">Docker Build</div>
              <p class="text-[11px] text-dock-text-dim">Compila a nova imagem</p>
            </div>
            <div class="p-3.5 rounded-xl bg-dock-surface/40 border border-dock-border text-center space-y-1">
              <div class="font-bold text-xs text-dock-accent">Etapa 4</div>
              <div class="font-semibold text-sm text-dock-text">Substituição</div>
              <p class="text-[11px] text-dock-text-dim">Troca do contêiner ativo</p>
            </div>
            <div class="p-3.5 rounded-xl bg-dock-surface/40 border border-dock-border text-center space-y-1">
              <div class="font-bold text-xs text-dock-success">Etapa 5</div>
              <div class="font-semibold text-sm text-dock-text">Health Check</div>
              <p class="text-[11px] text-dock-text-dim">Verifica se está respondendo</p>
            </div>
          </div>

          <div class="p-4 rounded-xl bg-dock-surface/50 border border-dock-border space-y-2">
            <h4 class="font-semibold text-sm text-dock-text flex items-center gap-2">
              <ShieldCheck class="w-4 h-4 text-dock-success" /> Rollback Automático em Caso de Erro
            </h4>
            <p class="text-xs text-dock-text-muted leading-relaxed">
              Se durante o Health Check a nova versão não responder dentro do tempo limite ou apresentar erros de inicialização, o DeployDock automaticamente reverte para a imagem anterior conhecida como saudável, garantindo <strong>zero downtime</strong> e estabilidade contínua.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Seção de Perguntas Frequentes (FAQ) -->
    <div class="glass-panel p-6 sm:p-8 space-y-4">
      <h3 class="text-lg font-bold text-dock-text flex items-center gap-2">
        <HelpCircle class="w-5 h-5 text-dock-accent" /> Perguntas Frequentes (FAQ)
      </h3>

      <div class="space-y-3">
        <div 
          v-for="(item, idx) in faqs" 
          :key="idx"
          class="border border-dock-border rounded-xl overflow-hidden transition-colors"
        >
          <button 
            @click="toggleFaq(idx)"
            class="w-full text-left px-4 py-3.5 bg-dock-surface/40 hover:bg-dock-surface/70 flex items-center justify-between text-sm font-medium text-dock-text cursor-pointer"
          >
            <span>{{ item.q }}</span>
            <span class="text-dock-text-dim text-lg leading-none">{{ openFaq === idx ? '−' : '+' }}</span>
          </button>
          <div 
            v-if="openFaq === idx" 
            class="px-4 py-3.5 bg-dock-bg/50 border-t border-dock-border text-xs text-dock-text-muted leading-relaxed"
          >
            {{ item.a }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
