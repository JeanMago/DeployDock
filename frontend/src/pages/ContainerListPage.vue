<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Grid, List, Search, RefreshCw, Box, Plus, X, Play } from 'lucide-vue-next';
import ContainerCard from '@/components/containers/ContainerCard.vue';
import ContainerTable from '@/components/containers/ContainerTable.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import { api } from '@/services/api';
import type { Container } from '@/services/types';

const viewMode = ref<'grid' | 'table'>('grid');
const containers = ref<Container[]>([]);
const search = ref('');
const filter = ref('all');
const loading = ref(true);

// Modal Lançador Rápido de Contêiner (Docker Hub)
const showQuickRunModal = ref(false);
const runningQuick = ref(false);
const quickForm = ref({
  image: 'redis:alpine',
  name: '',
  host_port: null as number | null,
  container_port: 6379 as number | null,
  env_text: '',
  restart_policy: 'unless-stopped',
});

const quickPresets = [
  { label: 'Redis Cache', image: 'redis:alpine', name: 'redis-cache', hostPort: 6379, containerPort: 6379, env: '' },
  { label: 'Nginx Web', image: 'nginx:alpine', name: 'nginx-web', hostPort: 8085, containerPort: 80, env: '' },
  { label: 'Adminer DB UI', image: 'adminer:latest', name: 'adminer-sql', hostPort: 8086, containerPort: 8080, env: '' },
  {
    label: 'PostgreSQL 15',
    image: 'postgres:15-alpine',
    name: 'postgres-dev',
    hostPort: 5433,
    containerPort: 5432,
    env: 'POSTGRES_USER=admin\nPOSTGRES_PASSWORD=secret\nPOSTGRES_DB=appdb',
  },
  { label: 'MailHog SMTP', image: 'mailhog/mailhog', name: 'mailhog-smtp', hostPort: 8025, containerPort: 8025, env: '' },
];

const applyPreset = (p: (typeof quickPresets)[0]) => {
  quickForm.value.image = p.image;
  quickForm.value.name = p.name;
  quickForm.value.host_port = p.hostPort;
  quickForm.value.container_port = p.containerPort;
  quickForm.value.env_text = p.env;
};

const submitQuickRun = async () => {
  if (!quickForm.value.image.trim()) {
    alert('Informe a imagem Docker.');
    return;
  }
  runningQuick.value = true;
  try {
    await api.containers.runQuick({
      image: quickForm.value.image.trim(),
      name: quickForm.value.name.trim() || undefined,
      host_port: quickForm.value.host_port,
      container_port: quickForm.value.container_port,
      env_text: quickForm.value.env_text,
      restart_policy: quickForm.value.restart_policy,
    });
    showQuickRunModal.value = false;
    await load();
  } catch (e: any) {
    alert(e?.message || 'Erro ao iniciar contêiner');
  } finally {
    runningQuick.value = false;
  }
};

const load = async () => {
  loading.value = true;
  try {
    containers.value = await api.containers.list();
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

onMounted(load);

const filtered = computed(() => {
  return containers.value.filter((c) => {
    const mSearch =
      c.name.toLowerCase().includes(search.value.toLowerCase()) ||
      c.image.toLowerCase().includes(search.value.toLowerCase());
    const mFilter = filter.value === 'all' || c.state === filter.value;
    return mSearch && mFilter;
  });
});

const handleAction = async (action: string, id: string) => {
  const actionNames: Record<string, string> = {
    start: 'iniciar',
    stop: 'parar',
    restart: 'reiniciar',
    remove: 'remover',
  };
  const label = actionNames[action] || action;
  if (['stop', 'remove'].includes(action) && !confirm(`Deseja realmente ${label} este contêiner?`))
    return;
  try {
    await (api.containers as any)[action](id);
    load();
  } catch (e) {
    alert('Erro ao executar ação: ' + e);
  }
};
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col sm:flex-row justify-between gap-3">
      <div class="flex items-center gap-3 glass-panel p-1 rounded-md">
        <div class="relative flex-1 sm:w-64">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-dock-text-dim" />
          <input
            v-model="search"
            type="text"
            placeholder="Buscar contêineres..."
            class="w-full bg-transparent border-none focus:ring-0 pl-8 pr-3 py-1.5 text-xs text-dock-text placeholder-dock-text-dim outline-none"
          />
        </div>
        <div class="w-px h-4 bg-dock-border"></div>
        <select
          v-model="filter"
          class="bg-transparent border-none text-xs text-dock-text focus:ring-0 outline-none pr-3 cursor-pointer"
        >
          <option value="all" class="bg-dock-bg">Todos os Status</option>
          <option value="running" class="bg-dock-bg">Em Execução</option>
          <option value="exited" class="bg-dock-bg">Parados</option>
        </select>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="showQuickRunModal = true"
          class="px-3 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <Plus class="w-3.5 h-3.5" /> Lançar Contêiner
        </button>

        <button
          @click="load"
          class="p-2 glass-panel hover:bg-dock-surface text-dock-text-muted hover:text-dock-text transition-colors cursor-pointer"
          title="Atualizar"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
        </button>
        <div class="flex glass-panel p-1 rounded-md">
          <button
            @click="viewMode = 'grid'"
            class="p-1.5 rounded transition-colors cursor-pointer"
            :class="
              viewMode === 'grid'
                ? 'bg-dock-surface text-dock-text'
                : 'text-dock-text-muted hover:text-dock-text'
            "
            title="Visualização em Grade"
          >
            <Grid class="w-3.5 h-3.5" />
          </button>
          <button
            @click="viewMode = 'table'"
            class="p-1.5 rounded transition-colors cursor-pointer"
            :class="
              viewMode === 'table'
                ? 'bg-dock-surface text-dock-text'
                : 'text-dock-text-muted hover:text-dock-text'
            "
            title="Visualização em Tabela"
          >
            <List class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-20"><LoadingSpinner /></div>
    <div v-else-if="!filtered.length">
      <EmptyState
        :icon="Box"
        title="Nenhum contêiner encontrado"
        description="Nenhum contêiner corresponde à busca ou o Docker não possui contêineres ativos no momento."
      />
    </div>
    <div v-else>
      <div
        v-if="viewMode === 'grid'"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
      >
        <ContainerCard v-for="c in filtered" :key="c.id" :container="c" @action="handleAction" />
      </div>
      <ContainerTable v-else :containers="filtered" @action="handleAction" />
    </div>

    <!-- Modal: Lançar Contêiner Rápido (Docker Hub) -->
    <div
      v-if="showQuickRunModal"
      class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      @click.self="showQuickRunModal = false"
    >
      <div class="w-full max-w-lg bg-dock-surface border border-dock-border-light rounded-lg shadow-2xl overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b border-dock-border bg-dock-bg">
          <div>
            <h3 class="text-sm font-semibold text-dock-text">Lançar Contêiner (Docker Hub)</h3>
            <p class="text-[11px] text-dock-text-dim">
              Baixa a imagem automaticamente e inicia com isolamento `no-new-privileges`
            </p>
          </div>
          <button
            @click="showQuickRunModal = false"
            class="p-1 rounded text-dock-text-dim hover:text-dock-text cursor-pointer"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="p-4 space-y-3.5 text-xs">
          <!-- Presets 1-Click -->
          <div>
            <div class="text-[11px] font-mono text-dock-text-dim mb-1.5">Presets Rápidos:</div>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="p in quickPresets"
                :key="p.label"
                @click="applyPreset(p)"
                class="px-2 py-1 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-[11px] font-mono text-dock-text-muted hover:text-dock-text transition-colors cursor-pointer"
              >
                {{ p.label }}
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-dock-text-muted mb-1">Imagem Docker *</label>
              <input
                v-model="quickForm.image"
                type="text"
                placeholder="ex: redis:alpine"
                class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Nome do Contêiner (opcional)</label>
              <input
                v-model="quickForm.name"
                type="text"
                placeholder="ex: meu-redis"
                class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
              />
            </div>
          </div>

          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="block text-dock-text-muted mb-1">Porta Host</label>
              <input
                v-model.number="quickForm.host_port"
                type="number"
                placeholder="ex: 6379"
                class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Porta Contêiner</label>
              <input
                v-model.number="quickForm.container_port"
                type="number"
                placeholder="ex: 6379"
                class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Restart Policy</label>
              <select
                v-model="quickForm.restart_policy"
                class="w-full bg-dock-bg border border-dock-border rounded px-2 py-1.5 font-mono text-dock-text outline-none"
              >
                <option value="unless-stopped">unless-stopped</option>
                <option value="always">always</option>
                <option value="on-failure">on-failure</option>
                <option value="no">no</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-dock-text-muted mb-1">Variáveis de Ambiente (KEY=VALUE por linha)</label>
            <textarea
              v-model="quickForm.env_text"
              rows="3"
              placeholder="POSTGRES_PASSWORD=secret&#10;TZ=America/Sao_Paulo"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
            ></textarea>
          </div>
        </div>

        <div class="px-4 py-3 border-t border-dock-border bg-dock-bg flex items-center justify-end gap-2">
          <button
            @click="showQuickRunModal = false"
            class="px-3 py-1.5 rounded bg-dock-surface border border-dock-border text-xs text-dock-text-muted hover:text-dock-text cursor-pointer"
          >
            Cancelar
          </button>
          <button
            @click="submitQuickRun"
            :disabled="runningQuick"
            class="px-3.5 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white text-xs font-medium flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
          >
            <Play class="w-3.5 h-3.5" />
            {{ runningQuick ? 'Baixando & Iniciando...' : 'Iniciar Contêiner' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
