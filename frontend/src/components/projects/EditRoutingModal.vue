<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { X, Globe, Save, Check, AlertCircle, ExternalLink } from 'lucide-vue-next';
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
    const updated = await api.projects.update(propsData.project.id, {
      subdomain: subdomain.value.trim() || undefined,
      custom_domain: customDomain.value.trim() || undefined,
      container_port: containerPort.value ? Number(containerPort.value) : undefined,
    });

    success.value = true;
    props('updated', updated);
    setTimeout(() => {
      props('close');
    }, 1200);
  } catch (err: any) {
    error.value = err?.message || 'Falha ao salvar as configurações de URL.';
  } finally {
    isSaving.value = false;
  }
};
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
    <div class="glass-panel w-full max-w-lg bg-dock-bg/95 border border-dock-border-light shadow-2xl rounded-2xl overflow-hidden flex flex-col">
      <!-- Cabeçalho -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-dock-border bg-dock-surface/40">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-dock-accent/15 text-dock-accent">
            <Globe class="w-5 h-5" />
          </div>
          <div>
            <h3 class="text-base font-bold text-dock-text">Editar URL da Aplicação</h3>
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
      <div class="p-6 space-y-5">
        <!-- Notificação de Erro / Sucesso -->
        <div v-if="error" class="p-3 rounded-lg bg-dock-error/15 border border-dock-error/30 text-dock-error text-xs flex items-start gap-2">
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ error }}</span>
        </div>

        <div v-if="success" class="p-3 rounded-lg bg-dock-success/15 border border-dock-success/30 text-dock-success text-xs flex items-center gap-2">
          <Check class="w-4 h-4 shrink-0" />
          <span>URL atualizada com sucesso! O roteamento foi aplicado.</span>
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
          <label class="block text-xs font-medium text-dock-text">
            Subdomínio da Aplicação
          </label>
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
          <p class="text-[11px] text-dock-text-dim">
            Localmente no navegador funciona com qualquer <code class="text-dock-accent">.localhost</code> sem precisar configurar DNS. Em produção usará o domínio base configurado.
          </p>
        </div>

        <!-- Domínio Personalizado (opcional) -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label class="block text-xs font-medium text-dock-text">
              Domínio Personalizado (Produção)
            </label>
            <span class="text-[10px] text-dock-text-dim uppercase tracking-wider">Opcional</span>
          </div>
          <input
            v-model="customDomain"
            type="text"
            placeholder="ex: www.meusite.com.br"
            class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-sm text-dock-text outline-none font-mono"
          />
          <p class="text-[11px] text-dock-text-dim">
            Se preenchido, tem prioridade sobre o subdomínio. Em produção, aponte um registro DNS CNAME para o IP do servidor.
          </p>
        </div>

        <!-- Porta Interna do Contêiner -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label class="block text-xs font-medium text-dock-text">
              Porta Interna do Contêiner
            </label>
            <span class="text-[10px] text-dock-text-dim">Auto-detectada</span>
          </div>
          <input
            v-model="containerPort"
            type="number"
            placeholder="Padrão: 80 (ou EXPOSE do Dockerfile)"
            class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 text-sm text-dock-text outline-none font-mono"
          />
          <p class="text-[11px] text-dock-text-dim">
            Porta HTTP que a aplicação escuta internamente (ex: 80 para Nginx, 3000 para Node, 8000 para FastAPI).
          </p>
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
