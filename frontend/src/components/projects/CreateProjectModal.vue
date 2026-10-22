<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  X, Plus, Github, Layers, Code, Sparkles, Check, Copy, Rocket, Folder, Lock, Cpu
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { ProjectCreate } from '@/services/types';

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
  dockerfile_path: 'Dockerfile',
  docker_compose_path: 'docker-compose.yml',
  auto_deploy: true,
  preview_deployments_enabled: true,
  auto_heal: true,
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
    error.value = 'Por favor, informe a URL do repositório Git.';
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
      dockerfile_path: form.value.dockerfile_path || 'Dockerfile',
      docker_compose_path: form.value.docker_compose_path || 'docker-compose.yml',
      auto_deploy: form.value.auto_deploy,
      preview_deployments_enabled: form.value.preview_deployments_enabled,
      auto_heal: form.value.auto_heal,
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
    <div class="glass-panel w-full max-w-2xl bg-dock-bg/95 border border-dock-border-light shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <!-- Cabeçalho -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-dock-border bg-dock-surface/40">
        <div>
          <h3 class="text-lg font-bold text-dock-text flex items-center gap-2">
            <Plus class="w-5 h-5 text-dock-accent" /> Novo Projeto
          </h3>
          <p class="text-xs text-dock-text-dim mt-0.5">
            Crie um projeto 1-Click ou conecte seu repositório Git (público ou privado) com Quotas de CPU/RAM e Auto-Healing.
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
              class="flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all"
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
              class="flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all"
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
                <div class="text-sm font-semibold text-dock-text">Repositório Git (Público/Privado)</div>
                <div class="text-xs text-dock-text-dim">Clona do GitHub/GitLab + Preview Environments</div>
              </div>
            </button>
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

        <!-- Modo 2: Repositório Git -->
        <div v-else class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-dock-text-muted mb-1.5">
              URL do Repositório Git <span class="text-dock-accent">*</span>
            </label>
            <input
              v-model="form.repo_url"
              type="text"
              placeholder="https://github.com/usuario/repositorio.git"
              class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3.5 py-2.5 text-sm text-dock-text placeholder-dock-text-dim outline-none transition-colors"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-dock-text-muted mb-1.5 flex items-center gap-1.5">
              <Lock class="w-3.5 h-3.5 text-dock-accent" />
              Token de Acesso Git / PAT (Opcional — Para Repositórios Privados)
            </label>
            <input
              v-model="form.git_token"
              type="password"
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx ou glpat-xxxxxxxxxxxx"
              class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3.5 py-2 text-sm font-mono text-dock-text placeholder-dock-text-dim outline-none"
            />
            <p class="text-[11px] text-dock-text-dim mt-1">
              Criptografado em repouso com Fernet AES-128. Permite clonar repositórios privados do GitHub ou GitLab.
            </p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-dock-text-muted mb-1.5">Branch Monitorada</label>
              <input
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
