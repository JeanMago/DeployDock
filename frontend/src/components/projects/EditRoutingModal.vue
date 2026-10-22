<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { X, Globe, Save, Check, AlertCircle, ExternalLink, Cpu, Lock } from 'lucide-vue-next';
import { api } from '@/services/api';
import type { Project, RoutingConfig } from '@/services/types';

const props = defineEmits<{
  (e: 'close'): void;
  (e: 'updated', project: Project): void;
}>();

const propsData = defineProps<{
  project: Project;
}>();

const config = ref<RoutingConfig>({
  base_domain: 'localhost',
  tls_enabled: false,
  scheme: 'http',
  port_suffix: '',
});

const subdomain = ref(propsData.project.subdomain || '');
const customDomain = ref(propsData.project.custom_domain || '');
const containerPort = ref<number | undefined>(propsData.project.container_port || undefined);
const memoryLimitMb = ref<number | undefined>(propsData.project.memory_limit_mb || undefined);
const cpuLimitCores = ref<number | undefined>(propsData.project.cpu_limit_cores || undefined);
const gitToken = ref('');
const autoHeal = ref(propsData.project.auto_heal !== false);
const previewEnabled = ref(propsData.project.preview_deployments_enabled !== false);

const isSaving = ref(false);
const error = ref('');
const success = ref(false);

onMounted(async () => {
  try {
    config.value = await api.projects.getRoutingConfig();
  } catch (err) {
    console.warn('Não foi possível carregar routing-config do backend:', err);
  }
});

const calculatedSubdomainHost = computed(() => {
  const sub = subdomain.value.trim().toLowerCase() || 'app';
  return `${sub}.${config.value.base_domain}`;
});

const activeHost = computed(() => {
  if (customDomain.value.trim()) {
    return customDomain.value.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
  }
  return calculatedSubdomainHost.value;
});

const previewUrl = computed(() => {
  return `${config.value.scheme}://${activeHost.value}${config.value.port_suffix}`;
});

const handleSave = async () => {
  error.value = '';
  success.value = false;
  isSaving.value = true;

  try {
    const payload: any = {
      subdomain: subdomain.value.trim() || undefined,
      custom_domain: customDomain.value.trim() || undefined,
      container_port: containerPort.value ? Number(containerPort.value) : undefined,
      memory_limit_mb: memoryLimitMb.value ? Number(memoryLimitMb.value) : null,
      cpu_limit_cores: cpuLimitCores.value ? Number(cpuLimitCores.value) : null,
      auto_heal: autoHeal.value,
      preview_deployments_enabled: previewEnabled.value,
    };
    if (gitToken.value.trim()) {
      payload.git_token = gitToken.value.trim();
    }

    const updated = await api.projects.update(propsData.project.id, payload);

    success.value = true;
    props('updated', updated);
    setTimeout(() => {
      props('close');
    }, 1000);
  } catch (err: any) {
    error.value = err?.message || 'Falha ao salvar as configurações do projeto.';
  } finally {
    isSaving.value = false;
  }
};
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
    <div class="glass-panel w-full max-w-lg bg-dock-bg/95 border border-dock-border-light shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <!-- Cabeçalho -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-dock-border bg-dock-surface/40">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-dock-accent/15 text-dock-accent">
            <Globe class="w-5 h-5" />
          </div>
          <div>
            <h3 class="text-base font-bold text-dock-text">Configurar URL, Recursos & Git</h3>
            <p class="text-xs text-dock-text-dim">{{ project.name }}</p>
          </div>
        </div>
        <button
          @click="$emit('close')"
          class="p-1.5 text-dock-text-muted hover:text-dock-text rounded-lg hover:bg-dock-surface transition-colors"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Conteúdo -->
      <div class="p-6 space-y-4 overflow-y-auto flex-1">
        <!-- Notificação de Erro / Sucesso -->
        <div v-if="error" class="p-3 rounded-lg bg-dock-error/15 border border-dock-error/30 text-dock-error text-xs flex items-start gap-2">
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ error }}</span>
        </div>

        <div v-if="success" class="p-3 rounded-lg bg-dock-success/15 border border-dock-success/30 text-dock-success text-xs flex items-center gap-2">
          <Check class="w-4 h-4 shrink-0" />
          <span>Configurações atualizadas e aplicadas ao contêiner!</span>
        </div>

        <!-- Preview da URL Pública -->
        <div class="p-3.5 rounded-xl bg-dock-surface/50 border border-dock-border space-y-1.5">
          <div class="text-[11px] font-medium text-dock-text-dim flex items-center justify-between">
            <span>Pré-visualização do Link Rápido:</span>
            <a
              :href="previewUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="text-dock-accent hover:underline flex items-center gap-1"
            >
              Testar <ExternalLink class="w-3 h-3" />
            </a>
          </div>
          <div class="font-mono text-xs text-dock-accent break-all bg-dock-bg px-3 py-2 rounded-lg border border-dock-border select-all">
            {{ previewUrl }}
          </div>
        </div>

        <!-- Subdomínio -->
        <div class="space-y-1.5">
          <label class="block text-xs font-medium text-dock-text">Subdomínio da Aplicação</label>
          <div class="flex items-center">
            <input
              v-model="subdomain"
              type="text"
              placeholder="ex: meusite"
              class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-l-lg px-3 py-2 text-sm text-dock-text outline-none font-mono"
            />
            <span class="bg-dock-bg text-dock-text-dim border border-l-0 border-dock-border rounded-r-lg px-3 py-2 text-xs font-mono select-none">
              .{{ config.base_domain }}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <!-- Domínio Personalizado -->
          <div class="space-y-1.5">
            <label class="block text-xs font-medium text-dock-text">Domínio Próprio (Opcional)</label>
            <input
              v-model="customDomain"
              type="text"
              placeholder="www.meusite.com.br"
              class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-xs text-dock-text outline-none font-mono"
            />
          </div>

          <!-- Porta Interna -->
          <div class="space-y-1.5">
            <label class="block text-xs font-medium text-dock-text">Porta Interna do Contêiner</label>
            <input
              v-model="containerPort"
              type="number"
              placeholder="Auto (ex: 80, 3000, 8000)"
              class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-xs text-dock-text outline-none font-mono"
            />
          </div>
        </div>

        <!-- Limites de Recursos (Quotas de CPU & RAM) -->
        <div class="p-3.5 rounded-xl bg-dock-surface/40 border border-dock-border space-y-3">
          <div class="text-xs font-semibold text-dock-text flex items-center gap-1.5">
            <Cpu class="w-3.5 h-3.5 text-dock-accent" /> Quotas de CPU & Memória RAM
          </div>
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div>
              <label class="block text-dock-text-muted mb-1">Memória RAM Máx. (MB)</label>
              <input
                v-model.number="memoryLimitMb"
                type="number"
                min="32"
                max="65536"
                placeholder="Ex: 512"
                class="w-full bg-dock-surface border border-dock-border rounded-lg px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">CPU Máx. (vCPUs)</label>
              <input
                v-model.number="cpuLimitCores"
                type="number"
                step="0.25"
                min="0.1"
                max="32"
                placeholder="Ex: 1.0"
                class="w-full bg-dock-surface border border-dock-border rounded-lg px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
          </div>
          <div class="space-y-1.5 pt-1 text-xs">
            <label class="flex items-center gap-2 cursor-pointer text-dock-text-muted">
              <input type="checkbox" v-model="autoHeal" class="accent-dock-accent" />
              <span>Auto-Healing (reiniciar automaticamente se falhar 3x no Health Check)</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer text-dock-text-muted">
              <input type="checkbox" v-model="previewEnabled" class="accent-dock-accent" />
              <span>Permitir Preview Deployments por Branch / Pull Request</span>
            </label>
          </div>
        </div>

        <!-- Token Git Privado -->
        <div class="space-y-1.5">
          <label class="block text-xs font-medium text-dock-text flex items-center gap-1.5">
            <Lock class="w-3.5 h-3.5 text-dock-accent" />
            Token Git / PAT para Repositório Privado
            <span v-if="project.has_git_token" class="text-[10px] font-mono text-dock-success">(Token ativo)</span>
          </label>
          <input
            v-model="gitToken"
            type="password"
            placeholder="Deixe em branco para manter o atual ou cole novo token ghp_..."
            class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-xs text-dock-text outline-none font-mono"
          />
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
          :disabled="isSaving"
          @click="handleSave"
          class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-dock-accent hover:bg-dock-accent-hover text-white shadow-lg shadow-dock-accent/20 transition-colors disabled:opacity-50"
        >
          <Save class="w-4 h-4" />
          {{ isSaving ? 'Salvando...' : 'Salvar Alterações' }}
        </button>
      </div>
    </div>
  </div>
</template>
