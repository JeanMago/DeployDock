<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import {
  X,
  Plus,
  Github,
  Layers,
  Code,
  Sparkles,
  Check,
  Copy,
  Rocket,
  Folder,
  Lock,
  Cpu,
  RefreshCw,
  ExternalLink,
  KeyRound,
  Search,
  CheckCircle2,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type {
  ProjectCreate,
  GitHubIntegrationStatus,
  GitHubRepoItem,
  GitHubRepoInspection,
} from '@/services/types';

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'created', project: any): void;
}>();

const mode = ref<'template' | 'git'>('template');
const selectedTemplate = ref<'static' | 'fastapi' | 'express' | 'flask' | 'adminer' | 'status_page' | 'custom'>('static');

const form = ref({
  name: '',
  subdomain: '',
  custom_domain: '',
  repo_url: '',
  branch: 'main',
  git_token: '',
  container_port: undefined as number | undefined,
  dockerfile_path: 'Dockerfile',
  docker_compose_path: 'docker-compose.yml',
  auto_deploy: true,
  preview_deployments_enabled: true,
  auto_heal: true,
  blue_green: false,
  memory_limit_mb: undefined as number | undefined,
  cpu_limit_cores: undefined as number | undefined,
  webhook_secret: generateSecret(),
  dockerfile_content: `# Dockerfile personalizado
FROM alpine:latest
CMD ["echo", "DeployDock custom container rodando!"]
`,
});

const isSubmitting = ref(false);
const error = ref('');
const copiedWebhook = ref(false);
const copiedSecret = ref(false);

// Estado da Integração Automática com GitHub
const ghStatus = ref<GitHubIntegrationStatus | null>(null);
const ghRepos = ref<GitHubRepoItem[]>([]);
const ghReposLoading = ref(false);
const ghSearchQuery = ref('');
const ghAccountFilter = ref('');
const ghQuickToken = ref('');
const showGhConnectBox = ref(false);
const ghDeviceFlow = ref<{
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
} | null>(null);
const ghDevicePolling = ref(false);
const ghDeviceStatusMsg = ref('');
const copiedDeviceCode = ref(false);
let devicePollTimer: ReturnType<typeof setInterval> | null = null;

// Resultado da Inspeção Automática do Código no GitHub
const repoInspection = ref<GitHubRepoInspection | null>(null);
const inspectingRepo = ref(false);
const discoveredEnvVars = ref<{ key: string; value: string; is_secret: boolean }[]>([]);

function generateSecret(): string {
  const chars = 'abcdef0123456789';
  let str = '';
  for (let i = 0; i < 32; i++) {
    str += chars[Math.floor(Math.random() * chars.length)];
  }
  return str;
}

const webhookUrl = computed(() => {
  return `${window.location.origin}/api/v1/webhooks/github`;
});

const filteredGhRepos = computed(() => {
  const q = ghSearchQuery.value.trim().toLowerCase();
  if (!q) return ghRepos.value;
  return ghRepos.value.filter(
    (r) =>
      r.name.toLowerCase().includes(q) ||
      r.full_name.toLowerCase().includes(q) ||
      (r.language || '').toLowerCase().includes(q) ||
      (r.description || '').toLowerCase().includes(q)
  );
});

const startDevicePollingLoop = (intervalSec = 7) => {
  if (devicePollTimer) clearInterval(devicePollTimer);
  devicePollTimer = setInterval(async () => {
    try {
      const res = await api.paas.pollGithubDeviceFlow();
      if (res.status === 'connected') {
        if (devicePollTimer) clearInterval(devicePollTimer);
        ghDevicePolling.value = false;
        ghDeviceFlow.value = null;
        ghDeviceStatusMsg.value = '';
        showGhConnectBox.value = false;
        ghStatus.value = res.github;
        ghRepos.value = await api.paas.listGithubRepos();
      } else if (res.error_description) {
        ghDeviceStatusMsg.value = res.error_description;
      }
    } catch {
      // continua aguardando autorização
    }
  }, Math.max(7, intervalSec + 2) * 1000);
};

const loadGithubIntegration = async (customUser?: string) => {
  ghReposLoading.value = true;
  try {
    const st = await api.paas.githubStatus();
    ghStatus.value = st;
    if (!ghAccountFilter.value && st.username) {
      ghAccountFilter.value = st.username;
    }
    if (!st.connected && st.device_flow?.user_code) {
      ghDeviceFlow.value = st.device_flow;
      ghDevicePolling.value = true;
      showGhConnectBox.value = true;
      startDevicePollingLoop(st.device_flow.interval || 5);
    }
    const targetUser =
      customUser && customUser.toLowerCase() !== (st.username || '').toLowerCase()
        ? customUser
        : undefined;
    ghRepos.value = await api.paas.listGithubRepos(targetUser);
  } catch {
    // ignore
  } finally {
    ghReposLoading.value = false;
  }
};

onMounted(() => {
  loadGithubIntegration();
});

onUnmounted(() => {
  if (devicePollTimer) clearInterval(devicePollTimer);
});

watch(mode, (newMode) => {
  if (newMode === 'git' && ghRepos.value.length === 0) {
    loadGithubIntegration();
  }
});

const handleConnectGithubToken = async () => {
  if (!ghQuickToken.value.trim()) return;
  ghReposLoading.value = true;
  try {
    ghStatus.value = await api.paas.connectGithub({
      token: ghQuickToken.value.trim(),
      auto_inject_git_token: true,
      auto_create_webhook: true,
      auto_import_env_example: true,
    });
    ghQuickToken.value = '';
    showGhConnectBox.value = false;
    ghRepos.value = await api.paas.listGithubRepos();
  } catch (e: any) {
    error.value = e?.message || 'Erro ao autenticar token no GitHub.';
  } finally {
    ghReposLoading.value = false;
  }
};

const handleStartDeviceFlow = async () => {
  error.value = '';
  ghDeviceStatusMsg.value = '';
  try {
    const flow = await api.paas.startGithubDeviceFlow();
    ghDeviceFlow.value = flow;
    ghDevicePolling.value = true;
    try {
      await navigator.clipboard.writeText(flow.user_code);
      copiedDeviceCode.value = true;
    } catch {
      // ignore clipboard error
    }
    startDevicePollingLoop(flow.interval || 5);
  } catch (e: any) {
    error.value = e?.message || 'Falha ao iniciar autenticação OAuth Device no GitHub.';
  }
};

const handleManualPollDeviceFlow = async () => {
  ghDeviceStatusMsg.value = 'Verificando autorização junto ao GitHub...';
  try {
    const res = await api.paas.pollGithubDeviceFlow();
    if (res.status === 'connected') {
      if (devicePollTimer) clearInterval(devicePollTimer);
      ghDevicePolling.value = false;
      ghDeviceFlow.value = null;
      ghDeviceStatusMsg.value = '';
      showGhConnectBox.value = false;
      ghStatus.value = res.github;
      ghRepos.value = await api.paas.listGithubRepos();
    } else {
      ghDeviceStatusMsg.value =
        res.error_description || 'Ainda aguardando confirmação do código no GitHub...';
    }
  } catch (e: any) {
    ghDeviceStatusMsg.value = e?.message || 'Erro ao verificar autorização no GitHub.';
  }
};

const copyAndOpenGithubDevice = async () => {
  if (!ghDeviceFlow.value) return;
  try {
    await navigator.clipboard.writeText(ghDeviceFlow.value.user_code);
    copiedDeviceCode.value = true;
  } catch {
    // ignore
  }
  window.open(ghDeviceFlow.value.verification_uri, '_blank', 'noopener,noreferrer');
};

const selectGithubRepo = async (repo: GitHubRepoItem) => {
  form.value.repo_url = repo.clone_url;
  form.value.branch = repo.default_branch || 'main';
  if (!form.value.name.trim()) {
    form.value.name = repo.name.toLowerCase().replace(/[^a-z0-9-]/g, '-');
  }
  await inspectRepositoryCode(repo.full_name, repo.default_branch);
};

const inspectRepositoryCode = async (targetRepo?: string, targetBranch?: string) => {
  const repoRef = (targetRepo || form.value.repo_url || '').trim();
  if (!repoRef) return;
  inspectingRepo.value = true;
  try {
    const info = await api.paas.inspectGithubRepo(repoRef, targetBranch || form.value.branch);
    repoInspection.value = info;
    form.value.repo_url = info.clone_url || form.value.repo_url;
    form.value.branch = info.default_branch || form.value.branch;
    if (!form.value.name.trim() && info.name) {
      form.value.name = info.name.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    }
    if (info.detected_port && !form.value.container_port) {
      form.value.container_port = info.detected_port;
    }
    discoveredEnvVars.value = (info.discovered_env_vars || []).map((v) => ({ ...v }));
  } catch (e: any) {
    console.warn('Falha ao inspecionar repositório:', e);
  } finally {
    inspectingRepo.value = false;
  }
};

const copyToClipboard = (text: string, type: 'url' | 'secret') => {
  navigator.clipboard.writeText(text);
  if (type === 'url') {
    copiedWebhook.value = true;
    setTimeout(() => (copiedWebhook.value = false), 2000);
  } else {
    copiedSecret.value = true;
    setTimeout(() => (copiedSecret.value = false), 2000);
  }
};

const templates = [
  {
    id: 'static' as const,
    name: 'Site Estático / Nginx',
    desc: 'HTML, CSS e JavaScript servidos via Nginx Alpine',
    icon: Sparkles,
    tag: 'Nginx',
  },
  {
    id: 'fastapi' as const,
    name: 'Python (FastAPI)',
    desc: 'API REST assíncrona com Uvicorn e rota /health',
    icon: Code,
    tag: 'Python 3.11',
  },
  {
    id: 'express' as const,
    name: 'Node.js (Express)',
    desc: 'Servidor web leve em JavaScript / Node.js 20',
    icon: Layers,
    tag: 'Node.js 20',
  },
  {
    id: 'flask' as const,
    name: 'Python (Flask + Gunicorn)',
    desc: 'Microserviço web pronto para produção com Gunicorn',
    icon: Code,
    tag: 'Flask WSGI',
  },
  {
    id: 'adminer' as const,
    name: 'Adminer Database UI',
    desc: 'Painel web 1-Click para gerenciar PostgreSQL/MySQL/SQLite',
    icon: Layers,
    tag: '1-Click DB UI',
  },
  {
    id: 'status_page' as const,
    name: 'Status Page Operacional',
    desc: 'Página pública de status de infraestrutura pronta',
    icon: Sparkles,
    tag: '1-Click App',
  },
  {
    id: 'custom' as const,
    name: 'Dockerfile Personalizado',
    desc: 'Defina suas próprias instruções Docker diretamente na tela',
    icon: Folder,
    tag: 'Custom',
  },
];

const handleSubmit = async (triggerDeployNow: boolean = false) => {
  if (!form.value.name.trim()) {
    error.value = 'Por favor, informe o nome do projeto.';
    return;
  }

  if (mode.value === 'git' && !form.value.repo_url.trim()) {
    error.value = 'Por favor, selecione ou informe a URL do repositório Git.';
    return;
  }

  error.value = '';
  isSubmitting.value = true;

  try {
    const payload: ProjectCreate = {
      name: form.value.name.trim(),
      subdomain: form.value.subdomain.trim() || undefined,
      custom_domain: form.value.custom_domain.trim() || undefined,
      branch: form.value.branch.trim() || 'main',
      container_port: form.value.container_port ? Number(form.value.container_port) : undefined,
      dockerfile_path: form.value.dockerfile_path || 'Dockerfile',
      docker_compose_path: form.value.docker_compose_path || 'docker-compose.yml',
      auto_deploy: form.value.auto_deploy,
      preview_deployments_enabled: form.value.preview_deployments_enabled,
      auto_heal: form.value.auto_heal,
      deploy_strategy: form.value.blue_green ? 'blue_green' : 'recreate',
      memory_limit_mb: form.value.memory_limit_mb ? Number(form.value.memory_limit_mb) : undefined,
      cpu_limit_cores: form.value.cpu_limit_cores ? Number(form.value.cpu_limit_cores) : undefined,
      webhook_secret: form.value.webhook_secret,
    };

    if (mode.value === 'template') {
      payload.template = selectedTemplate.value;
      if (selectedTemplate.value === 'custom') {
        payload.dockerfile_content = form.value.dockerfile_content;
      }
    } else {
      payload.repo_url = form.value.repo_url.trim();
      if (form.value.git_token.trim()) {
        payload.git_token = form.value.git_token.trim();
      }
      if (discoveredEnvVars.value.length > 0) {
        payload.initial_env_vars = discoveredEnvVars.value.filter((item) => item.key.trim());
      }
    }

    const created = await api.projects.create(payload);

    if (triggerDeployNow) {
      try {
        await api.projects.triggerDeploy(created.id);
      } catch (depErr) {
        console.warn('Deploy automático não pôde ser iniciado imediatamente:', depErr);
      }
    }

    emit('created', created);
  } catch (err: any) {
    error.value = err?.message || 'Falha ao criar o projeto. Verifique os dados e tente novamente.';
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
    <div class="glass-panel w-full max-w-2xl bg-dock-bg/95 border border-dock-border-light shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[92vh]">
      <!-- Cabeçalho -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-dock-border bg-dock-surface/40">
        <div>
          <h3 class="text-lg font-bold text-dock-text flex items-center gap-2">
            <Plus class="w-5 h-5 text-dock-accent" /> Novo Projeto
          </h3>
          <p class="text-xs text-dock-text-dim mt-0.5">
            Crie um projeto 1-Click ou conecte seu GitHub com busca automática de repositórios, branches e variáveis de código
          </p>
        </div>
        <button
          @click="$emit('close')"
          class="p-1.5 text-dock-text-muted hover:text-dock-text rounded-lg hover:bg-dock-surface transition-colors"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Conteúdo com Scroll -->
      <div class="p-6 overflow-y-auto space-y-5 flex-1">
        <!-- Alerta de Erro -->
        <div v-if="error" class="p-3 rounded-lg bg-dock-error/15 border border-dock-error/30 text-dock-error text-xs">
          {{ error }}
        </div>

        <!-- Seletor de Modo -->
        <div>
          <label class="block text-xs font-medium text-dock-text-muted mb-2">Como deseja criar seu projeto?</label>
          <div class="grid grid-cols-2 gap-3">
            <button
              type="button"
              @click="mode = 'template'"
              class="flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all cursor-pointer"
              :class="
                mode === 'template'
                  ? 'bg-dock-accent/10 border-dock-accent text-dock-text shadow-sm'
                  : 'bg-dock-surface/50 border-dock-border text-dock-text-muted hover:border-dock-border-light'
              "
            >
              <div class="p-2 rounded-lg bg-dock-accent/20 text-dock-accent shrink-0">
                <Sparkles class="w-5 h-5" />
              </div>
              <div>
                <div class="text-sm font-semibold text-dock-text">Modelo Pronto (1-Click)</div>
                <div class="text-xs text-dock-text-dim">Criação instantânea gerenciada pelo DeployDock</div>
              </div>
            </button>

            <button
              type="button"
              @click="mode = 'git'"
              class="flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all cursor-pointer"
              :class="
                mode === 'git'
                  ? 'bg-dock-accent/10 border-dock-accent text-dock-text shadow-sm'
                  : 'bg-dock-surface/50 border-dock-border text-dock-text-muted hover:border-dock-border-light'
              "
            >
              <div class="p-2 rounded-lg bg-dock-surface text-dock-text shrink-0">
                <Github class="w-5 h-5" />
              </div>
              <div>
                <div class="text-sm font-semibold text-dock-text">Integração GitHub / Git</div>
                <div class="text-xs text-dock-text-dim">Busca automática de repos, autenticações e `.env`</div>
              </div>
            </button>
          </div>
        </div>

        <!-- Modo 2: Integração Automática com GitHub (Exibida no topo quando modo === 'git') -->
        <div v-if="mode === 'git'" class="p-4 rounded-xl bg-dock-surface/50 border border-dock-accent/30 space-y-3.5 text-xs">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <Github class="w-4 h-4 text-dock-accent" />
              <span class="font-semibold text-dock-text">Integração GitHub Automática</span>
              <span
                v-if="ghStatus?.connected"
                class="px-2 py-0.5 rounded bg-dock-success/15 border border-dock-success/30 text-dock-success font-mono text-[10px] flex items-center gap-1"
              >
                <CheckCircle2 class="w-3 h-3" /> @{{ ghStatus.username }} Conectado (Auto-Auth Ativo)
              </span>
              <span
                v-else
                class="px-2 py-0.5 rounded bg-dock-bg border border-dock-border text-dock-text-dim font-mono text-[10px]"
              >
                Modo Público (@{{ ghAccountFilter || 'JeanMago' }})
              </span>
            </div>

            <div class="flex items-center gap-1.5">
              <button
                type="button"
                @click="showGhConnectBox = !showGhConnectBox"
                class="px-2.5 py-1 rounded bg-dock-accent/15 hover:bg-dock-accent/25 border border-dock-accent/30 text-dock-accent font-medium cursor-pointer"
              >
                {{ ghStatus?.connected ? 'Trocar Conta / Token' : 'Autenticar Conta GitHub' }}
              </button>
              <button
                type="button"
                @click="loadGithubIntegration(ghAccountFilter || undefined)"
                :disabled="ghReposLoading"
                class="p-1.5 rounded bg-dock-bg hover:bg-dock-surface border border-dock-border text-dock-text-muted hover:text-dock-text cursor-pointer"
                title="Recarregar repositórios do GitHub"
              >
                <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': ghReposLoading }" />
              </button>
            </div>
          </div>

          <!-- Banner de Repositórios Privados se o token não tiver escopo 'repo' -->
          <div
            v-if="ghStatus?.connected && !ghStatus?.can_read_private_repos"
            class="p-2.5 rounded-lg bg-dock-warning/10 border border-dock-warning/30 text-xs text-dock-warning space-y-1.5"
          >
            <div class="flex items-center justify-between">
              <span class="font-semibold flex items-center gap-1.5">
                <Lock class="w-3.5 h-3.5" /> Desbloquear Repositórios Privados do GitHub
              </span>
              <a
                href="https://github.com/settings/tokens/new?description=DeployDock-Private-Repos&scopes=repo,read:user,admin:repo_hook,read:packages"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11px] underline flex items-center gap-1 font-medium"
              >
                Gerar Token com 'repo' <ExternalLink class="w-3 h-3" />
              </a>
            </div>
            <p class="text-[11px] text-dock-text-dim">
              O login via dispositivo autoriza apenas os repositórios públicos. Para listar e clonar seus <strong>repositórios privados</strong>, cole um Personal Access Token com permissão <code>repo</code>:
            </p>
            <div class="flex gap-2">
              <input
                v-model="ghQuickToken"
                type="password"
                placeholder="Cole aqui seu Token PAT (ghp_xxxx)..."
                class="flex-1 bg-dock-bg border border-dock-border rounded px-2.5 py-1 text-dock-text font-mono text-xs outline-none focus:border-dock-warning"
              />
              <button
                type="button"
                @click="handleConnectGithubToken"
                class="px-3 py-1 rounded bg-dock-warning text-black font-semibold text-xs cursor-pointer hover:opacity-90"
              >
                Ativar Privados
              </button>
            </div>
          </div>

          <!-- Caixa de Conexão OAuth Device Flow / Token Global -->
          <div v-if="showGhConnectBox" class="p-3 rounded-lg bg-dock-bg border border-dock-border space-y-3">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div class="font-semibold text-dock-text">1. Autenticação 1-Clique via Código do GitHub (OAuth Device Flow)</div>
                <div class="text-[11px] text-dock-text-dim">
                  Autorize diretamente no navegador sem precisar criar nem copiar tokens manualmente.
                </div>
              </div>
              <button
                type="button"
                @click="handleStartDeviceFlow"
                class="px-3 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium flex items-center gap-1.5 cursor-pointer shrink-0"
              >
                <Github class="w-3.5 h-3.5" /> Gerar Código de Autorização
              </button>
            </div>

            <div
              v-if="ghDeviceFlow"
              class="p-3.5 rounded-lg bg-dock-surface border-2 border-dock-accent space-y-2.5"
            >
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <div class="text-xs font-semibold text-dock-text">
                    Passo 1 — Copie este código gerado pelo DeployDock (ele <span class="text-dock-warning underline">não</span> vem pelo app do celular):
                  </div>
                  <div class="text-2xl font-mono font-bold tracking-widest text-dock-accent mt-1 select-all">
                    {{ ghDeviceFlow.user_code }}
                  </div>
                  <div v-if="copiedDeviceCode" class="text-[11px] text-dock-success font-mono mt-0.5">
                    ✓ Código {{ ghDeviceFlow.user_code }} já copiado para sua área de transferência (basta dar Ctrl+V no GitHub)!
                  </div>
                </div>
                <button
                  type="button"
                  @click="copyAndOpenGithubDevice"
                  class="px-4 py-2.5 rounded-lg bg-dock-success hover:opacity-90 text-white font-semibold flex items-center gap-1.5 cursor-pointer shrink-0 shadow-lg"
                >
                  <Copy class="w-4 h-4" />
                  Passo 2: Copiar {{ ghDeviceFlow.user_code }} e Abrir GitHub
                  <ExternalLink class="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  @click="handleManualPollDeviceFlow"
                  class="px-3.5 py-2.5 rounded-lg bg-dock-success text-white font-semibold text-xs hover:opacity-90 transition-opacity flex items-center gap-2 cursor-pointer shadow-sm"
                >
                  <CheckCircle2 class="w-4 h-4" />
                  Passo 3: Já Autorizei — Atualizar Acesso
                </button>
              </div>
              <div class="text-[11px] text-dock-text-dim flex items-center gap-2">
                <RefreshCw class="w-3 h-3 animate-spin text-dock-accent" />
                <span>
                  {{
                    ghDeviceStatusMsg ||
                    `Aguardando você colar o código ${ghDeviceFlow.user_code} em github.com/login/device e clicar em "Authorize"...`
                  }}
                </span>
              </div>
            </div>

            <div class="border-t border-dock-border pt-2.5 space-y-1.5">
              <div class="flex items-center justify-between">
                <span class="font-semibold text-dock-text">2. Ou use um Personal Access Token (PAT) do GitHub</span>
                <a
                  href="https://github.com/settings/tokens/new?description=DeployDock-PaaS&scopes=repo,read:user,admin:repo_hook,read:packages"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-[11px] text-dock-accent hover:underline flex items-center gap-1"
                >
                  Gerar Token no GitHub em 1 clique <ExternalLink class="w-3 h-3" />
                </a>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="ghQuickToken"
                  type="password"
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx ou github_pat_xxxx"
                  class="flex-1 bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
                />
                <button
                  type="button"
                  @click="handleConnectGithubToken"
                  class="px-3 py-1.5 rounded bg-dock-success/20 hover:bg-dock-success/30 border border-dock-success/40 text-dock-success font-medium cursor-pointer"
                >
                  Salvar e Autenticar
                </button>
              </div>
            </div>
          </div>

          <!-- Seletor de Repositórios do GitHub -->
          <div class="space-y-2">
            <div class="flex flex-wrap items-center gap-2">
              <div class="relative flex-1 min-w-[180px]">
                <Search class="w-3.5 h-3.5 text-dock-text-dim absolute left-2.5 top-2" />
                <input
                  v-model="ghSearchQuery"
                  type="text"
                  placeholder="Filtrar repositórios por nome ou linguagem..."
                  class="w-full bg-dock-bg border border-dock-border rounded pl-8 pr-2.5 py-1.5 text-dock-text outline-none focus:border-dock-accent"
                />
              </div>
              <div v-if="!ghStatus?.connected" class="flex items-center gap-1.5">
                <input
                  v-model="ghAccountFilter"
                  type="text"
                  placeholder="Usuário GitHub (ex: JeanMago)"
                  class="w-36 bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
                  @keyup.enter="loadGithubIntegration(ghAccountFilter)"
                />
                <button
                  type="button"
                  @click="loadGithubIntegration(ghAccountFilter)"
                  class="px-2.5 py-1.5 rounded bg-dock-bg hover:bg-dock-surface border border-dock-border text-dock-text cursor-pointer"
                >
                  Buscar Conta
                </button>
              </div>
            </div>

            <div v-if="ghRepos.length > 0" class="flex items-center justify-between text-[11px] text-dock-text-dim px-0.5">
              <span>{{ ghRepos.length }} repositórios carregados ({{ ghRepos.filter((r) => r.private).length }} privados)</span>
              <span v-if="ghStatus?.connected" class="text-dock-success flex items-center gap-1">
                <CheckCircle2 class="w-3 h-3" /> @{{ ghStatus.username }} sincronizado
              </span>
            </div>

            <div v-if="ghReposLoading" class="py-4 text-center text-dock-text-dim">
              Buscando repositórios e autenticações no GitHub...
            </div>
            <div
              v-else-if="filteredGhRepos.length > 0"
              class="max-h-40 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-1.5 pr-1"
            >
              <button
                v-for="repo in filteredGhRepos"
                :key="repo.id"
                type="button"
                @click="selectGithubRepo(repo)"
                class="p-2 rounded border text-left transition-all flex items-center justify-between gap-2 cursor-pointer"
                :class="
                  form.repo_url === repo.clone_url
                    ? 'bg-dock-accent/15 border-dock-accent text-dock-text'
                    : 'bg-dock-bg/80 border-dock-border hover:border-dock-border-light text-dock-text-muted'
                "
              >
                <div class="min-w-0">
                  <div class="font-mono font-semibold text-dock-text truncate flex items-center gap-1">
                    <Lock v-if="repo.private" class="w-3 h-3 text-dock-warning shrink-0" />
                    <span class="truncate">{{ repo.name }}</span>
                  </div>
                  <div class="text-[10px] text-dock-text-dim truncate">
                    {{ repo.language }} • branch: {{ repo.default_branch }}
                  </div>
                </div>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-dock-surface border border-dock-border text-dock-accent shrink-0">
                  Usar
                </span>
              </button>
            </div>
          </div>

          <!-- Resultado da Inspeção Automática do Código e Autenticações (.env.example) -->
          <div
            v-if="inspectingRepo"
            class="p-2.5 rounded bg-dock-bg border border-dock-border text-dock-accent font-mono text-[11px] flex items-center gap-2"
          >
            <RefreshCw class="w-3.5 h-3.5 animate-spin" />
            Analisando código do repositório, branches, Dockerfile e chaves `.env`...
          </div>
          <div
            v-else-if="repoInspection"
            class="p-3 rounded-lg bg-dock-bg border border-dock-success/30 space-y-2.5"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="font-mono font-semibold text-dock-success flex items-center gap-1.5">
                <CheckCircle2 class="w-3.5 h-3.5" />
                {{ repoInspection.full_name }} • {{ repoInspection.detected_stack }}
              </div>
              <span
                v-if="repoInspection.using_saved_github_token"
                class="px-2 py-0.5 rounded bg-dock-accent/15 text-dock-accent font-mono text-[10px]"
              >
                Credencial GitHub Automática Vinculada
              </span>
            </div>

            <!-- Variáveis e Chaves de Autenticação extraídas automaticamente do código (.env.example) -->
            <div v-if="discoveredEnvVars.length > 0" class="space-y-1.5 pt-1 border-t border-dock-border">
              <div class="text-[11px] font-semibold text-dock-text flex items-center gap-1.5">
                <KeyRound class="w-3.5 h-3.5 text-dock-warning" />
                Autenticações e Variáveis Detectadas no Código ({{ repoInspection.env_file_found }}) — Serão Importadas Automaticamente:
              </div>
              <div class="max-h-36 overflow-y-auto space-y-1.5 pr-1">
                <div
                  v-for="(ev, idx) in discoveredEnvVars"
                  :key="idx"
                  class="grid grid-cols-12 gap-1.5 items-center font-mono text-[11px]"
                >
                  <input
                    v-model="ev.key"
                    type="text"
                    class="col-span-5 bg-dock-surface border border-dock-border rounded px-2 py-1 text-dock-accent"
                  />
                  <input
                    v-model="ev.value"
                    :type="ev.is_secret ? 'text' : 'text'"
                    placeholder="Valor da variável / chave"
                    class="col-span-6 bg-dock-surface border border-dock-border rounded px-2 py-1 text-dock-text"
                  />
                  <span
                    class="col-span-1 text-center text-[10px]"
                    :class="ev.is_secret ? 'text-dock-warning' : 'text-dock-text-dim'"
                    :title="ev.is_secret ? 'Cifrada com Fernet AES-128' : 'Variável padrão'"
                  >
                    {{ ev.is_secret ? '🔒' : 'ENV' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Nome do Projeto -->
        <div>
          <label class="block text-xs font-medium text-dock-text-muted mb-1.5">
            Nome do Projeto <span class="text-dock-accent">*</span>
          </label>
          <input
            v-model="form.name"
            type="text"
            placeholder="Ex: meu-app-web, api-node, sistema-loja"
            class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3.5 py-2.5 text-sm text-dock-text placeholder-dock-text-dim outline-none transition-colors"
          />
        </div>

        <!-- URL Pública / Subdomínio -->
        <div class="p-3.5 rounded-xl bg-dock-surface/40 border border-dock-border space-y-2">
          <label class="block text-xs font-medium text-dock-text">
            URL Rápida da Aplicação (Subdomínio)
          </label>
          <div class="flex items-center">
            <input
              v-model="form.subdomain"
              type="text"
              :placeholder="form.name ? form.name.toLowerCase().replace(/[^a-z0-9]/g, '-') : 'meu-site'"
              class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-l-lg px-3 py-2 text-sm text-dock-text outline-none font-mono"
            />
            <span class="bg-dock-bg text-dock-text-dim border border-l-0 border-dock-border rounded-r-lg px-3 py-2 text-xs font-mono select-none">
              .localhost
            </span>
          </div>
          <p class="text-[11px] text-dock-text-dim">
            Deixe em branco para gerar automaticamente do nome. Você poderá alterar e adicionar domínios próprios a qualquer momento.
          </p>
        </div>

        <!-- Modo 1: Escolha do Modelo -->
        <div v-if="mode === 'template'" class="space-y-4">
          <label class="block text-xs font-medium text-dock-text-muted">Selecione o Modelo de Aplicação</label>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div
              v-for="tpl in templates"
              :key="tpl.id"
              @click="selectedTemplate = tpl.id"
              class="p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between"
              :class="
                selectedTemplate === tpl.id
                  ? 'bg-dock-accent/10 border-dock-accent shadow-sm'
                  : 'bg-dock-surface/50 border-dock-border hover:border-dock-border-light'
              "
            >
              <div class="flex items-start justify-between mb-2">
                <div class="p-2 rounded-lg bg-dock-surface border border-dock-border text-dock-accent">
                  <component :is="tpl.icon" class="w-4 h-4" />
                </div>
                <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-dock-surface border border-dock-border text-dock-text-dim">
                  {{ tpl.tag }}
                </span>
              </div>
              <h4 class="font-semibold text-sm text-dock-text">{{ tpl.name }}</h4>
              <p class="text-xs text-dock-text-dim mt-1">{{ tpl.desc }}</p>
            </div>
          </div>

          <!-- Editor Dockerfile Customizado -->
          <div v-if="selectedTemplate === 'custom'" class="mt-4">
            <label class="block text-xs font-medium text-dock-text-muted mb-1.5">Conteúdo do Dockerfile</label>
            <textarea
              v-model="form.dockerfile_content"
              rows="5"
              class="w-full bg-[#070b14] border border-dock-border focus:border-dock-accent rounded-lg p-3 font-mono text-xs text-dock-text placeholder-dock-text-dim outline-none transition-colors"
            ></textarea>
          </div>
        </div>

        <!-- Modo 2: Campos de URL, Branch e Token -->
        <div v-else class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-dock-text-muted mb-1.5">
              URL do Repositório Git <span class="text-dock-accent">*</span>
            </label>
            <div class="flex gap-2">
              <input
                v-model="form.repo_url"
                type="text"
                placeholder="https://github.com/usuario/repositorio.git"
                class="flex-1 bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3.5 py-2.5 text-sm text-dock-text placeholder-dock-text-dim outline-none transition-colors font-mono"
              />
              <button
                type="button"
                @click="inspectRepositoryCode()"
                :disabled="inspectingRepo || !form.repo_url.trim()"
                class="px-3 py-2 rounded-lg bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-medium text-dock-accent cursor-pointer shrink-0"
                title="Ler branches, Dockerfile e variáveis .env.example diretamente do código no GitHub"
              >
                {{ inspectingRepo ? '...' : 'Ler Código & Auth' }}
              </button>
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-dock-text-muted mb-1.5 flex items-center justify-between">
              <span class="flex items-center gap-1.5">
                <Lock class="w-3.5 h-3.5 text-dock-accent" />
                Token de Acesso Git Individual (Opcional)
              </span>
              <span v-if="ghStatus?.connected" class="text-[11px] font-mono text-dock-success">
                ✓ Autenticação GitHub Global ativa (@{{ ghStatus.username }})
              </span>
            </label>
            <input
              v-model="form.git_token"
              type="password"
              :placeholder="
                ghStatus?.connected
                  ? 'Deixe em branco para usar automaticamente a autenticação global do GitHub'
                  : 'ghp_xxxxxxxxxxxxxxxxxxxx ou glpat-xxxxxxxxxxxx'
              "
              class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3.5 py-2 text-sm font-mono text-dock-text placeholder-dock-text-dim outline-none"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-dock-text-muted mb-1.5">Branch Monitorada</label>
              <select
                v-if="repoInspection?.branches?.length"
                v-model="form.branch"
                @change="inspectRepositoryCode(repoInspection.full_name, form.branch)"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3.5 py-2 text-sm font-mono text-dock-text outline-none"
              >
                <option v-for="b in repoInspection.branches" :key="b" :value="b">{{ b }}</option>
              </select>
              <input
                v-else
                v-model="form.branch"
                type="text"
                placeholder="main"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3.5 py-2 text-sm text-dock-text outline-none"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-dock-text-muted mb-1.5">Arquivo de Build</label>
              <input
                v-model="form.dockerfile_path"
                type="text"
                placeholder="Dockerfile"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3.5 py-2 text-sm text-dock-text outline-none"
              />
            </div>
          </div>
        </div>

        <!-- Quotas de Recursos (CPU & RAM) + Auto-Healing -->
        <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-3">
          <div class="flex items-center justify-between">
            <span class="font-medium text-xs uppercase tracking-wider text-dock-text flex items-center gap-1.5">
              <Cpu class="w-3.5 h-3.5 text-dock-accent" /> Quotas de Recursos (CPU/RAM) & Auto-Healing
            </span>
            <span class="text-[10px] font-mono text-dock-text-dim">Proteção contra sobrecarga</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label class="block text-dock-text-muted mb-1">Limite de Memória RAM (MB)</label>
              <input
                v-model.number="form.memory_limit_mb"
                type="number"
                min="32"
                max="65536"
                placeholder="Ex: 512 (vazio = ilimitado)"
                class="w-full bg-dock-surface border border-dock-border rounded-lg px-3 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Limite de CPU (vCPUs)</label>
              <input
                v-model.number="form.cpu_limit_cores"
                type="number"
                step="0.25"
                min="0.1"
                max="32"
                placeholder="Ex: 1.0 (vazio = ilimitado)"
                class="w-full bg-dock-surface border border-dock-border rounded-lg px-3 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
              />
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-3 pt-1 text-xs">
            <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text-muted">
              <input type="checkbox" v-model="form.auto_heal" class="accent-dock-accent" />
              <span>Auto-Healing ativo (reiniciar contêiner se falhar no Health Check)</span>
            </label>
            <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text-muted">
              <input type="checkbox" v-model="form.blue_green" class="accent-dock-accent" />
              <span>Deploy Blue/Green (sem downtime: valida a nova versão antes de remover a antiga)</span>
            </label>
            <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text-muted">
              <input type="checkbox" v-model="form.preview_deployments_enabled" class="accent-dock-accent" />
              <span>Habilitar Preview Deployments por Branch / PR</span>
            </label>
          </div>
        </div>

        <!-- Automação & Webhook GitHub -->
        <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="font-medium text-sm text-dock-text">Integração Contínua (GitOps Webhook)</span>
              <span
                v-if="ghStatus?.connected && ghStatus?.auto_create_webhook"
                class="text-[10px] font-mono px-2 py-0.5 rounded bg-dock-success/15 text-dock-success"
              >
                Auto-Registro no GitHub Ativo
              </span>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="form.auto_deploy" class="sr-only peer" />
              <div class="w-9 h-5 bg-dock-surface peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-dock-border after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-dock-accent"></div>
            </label>
          </div>

          <div v-if="form.auto_deploy" class="pt-2 border-t border-dock-border/50 space-y-2 text-xs">
            <div>
              <div class="text-dock-text-dim mb-1 flex items-center justify-between">
                <span>Payload URL do Webhook:</span>
                <button
                  type="button"
                  @click="copyToClipboard(webhookUrl, 'url')"
                  class="text-dock-accent hover:underline flex items-center gap-1"
                >
                  <Check v-if="copiedWebhook" class="w-3 h-3 text-dock-success" />
                  <Copy v-else class="w-3 h-3" />
                  {{ copiedWebhook ? 'Copiado!' : 'Copiar URL' }}
                </button>
              </div>
              <div class="font-mono bg-dock-bg px-2.5 py-1.5 rounded border border-dock-border text-dock-text-muted truncate select-all">
                {{ webhookUrl }}
              </div>
            </div>

            <div>
              <div class="text-dock-text-dim mb-1 flex items-center justify-between">
                <span>Segredo do Webhook (Secret):</span>
                <button
                  type="button"
                  @click="copyToClipboard(form.webhook_secret, 'secret')"
                  class="text-dock-accent hover:underline flex items-center gap-1"
                >
                  <Check v-if="copiedSecret" class="w-3 h-3 text-dock-success" />
                  <Copy v-else class="w-3 h-3" />
                  {{ copiedSecret ? 'Copiado!' : 'Copiar Segredo' }}
                </button>
              </div>
              <div class="font-mono bg-dock-bg px-2.5 py-1.5 rounded border border-dock-border text-dock-text-muted truncate select-all">
                {{ form.webhook_secret }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Rodapé / Ações -->
      <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-dock-border bg-dock-surface/40">
        <button
          type="button"
          @click="$emit('close')"
          class="px-4 py-2 rounded-lg text-sm font-medium text-dock-text-muted hover:text-dock-text hover:bg-dock-surface transition-colors"
        >
          Cancelar
        </button>

        <button
          type="button"
          :disabled="isSubmitting"
          @click="handleSubmit(false)"
          class="px-4 py-2 rounded-lg text-sm font-medium bg-dock-surface hover:bg-dock-surface/80 text-dock-text border border-dock-border transition-colors disabled:opacity-50"
        >
          {{ isSubmitting ? 'Criando...' : 'Salvar Projeto' }}
        </button>

        <button
          type="button"
          :disabled="isSubmitting"
          @click="handleSubmit(true)"
          class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-dock-accent hover:bg-dock-accent-hover text-white shadow-lg shadow-dock-accent/20 transition-colors disabled:opacity-50"
        >
          <Rocket class="w-4 h-4" />
          {{ isSubmitting ? 'Iniciando...' : 'Criar e Fazer Deploy' }}
        </button>
      </div>
    </div>
  </div>
</template>
