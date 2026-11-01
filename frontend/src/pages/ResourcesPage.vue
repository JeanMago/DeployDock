<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import {
  Cpu,
  HardDrive,
  Server,
  RefreshCw,
  Trash2,
  Database,
  Layers,
  Box,
  FolderGit2,
  AlertTriangle,
  CheckCircle2,
  Download,
  Upload,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemResourcesOverview } from '@/services/types';
import StatusBadge from '@/components/common/StatusBadge.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const router = useRouter();
const data = ref<SystemResourcesOverview | null>(null);
const loading = ref(true);
const refreshing = ref(false);
const autoRefresh = ref(true);
const activeStorageTab = ref<'images' | 'volumes'>('images');
const pruningTarget = ref<string | null>(null);
const deletingId = ref<string | null>(null);
const feedbackMsg = ref<{ type: 'success' | 'error'; text: string } | null>(null);

let timer: ReturnType<typeof setInterval> | null = null;

const loadData = async (silent = false) => {
  if (!silent) loading.value = true;
  refreshing.value = true;
  try {
    data.value = await api.system.resources();
  } catch (err: any) {
    console.error('Erro ao carregar recursos:', err);
  } finally {
    loading.value = false;
    refreshing.value = false;
  }
};

const setupTimer = () => {
  if (timer) clearInterval(timer);
  if (autoRefresh.value) {
    timer = setInterval(() => loadData(true), 4000);
  }
};

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value;
  setupTimer();
};

onMounted(() => {
  loadData();
  setupTimer();
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});

const formatSizeMb = (mb: number | undefined | null): string => {
  const val = mb || 0;
  if (val >= 1024) {
    return `${(val / 1024).toFixed(2)} GB`;
  }
  if (val > 0 && val < 0.1) {
    return `${(val * 1024).toFixed(0)} KB`;
  }
  return `${val.toFixed(1)} MB`;
};

const formatUptime = (seconds: number): string => {
  if (!seconds) return '--';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  return `${h}h ${m}m`;
};

// Cálculos comparativos Host vs Docker
const nonDockerCpuPercent = computed(() => {
  if (!data.value) return 0;
  const hostCpu = data.value.host.cpu_percent;
  const dockerNorm = data.value.docker_usage.cpu_normalized_percent;
  return Math.max(0, +(hostCpu - dockerNorm).toFixed(1));
});

const nonDockerMemPercent = computed(() => {
  if (!data.value) return 0;
  const hostPct = data.value.host.memory_percent;
  const dockerPct = data.value.docker_usage.memory_share_of_host_percent;
  return Math.max(0, +(hostPct - dockerPct).toFixed(1));
});

const cachedMemPercent = computed(() => {
  if (!data.value || !data.value.host.memory_total_mb) return 0;
  const raw = (data.value.host.memory_cached_mb / data.value.host.memory_total_mb) * 100;
  const remaining = Math.max(0, 100 - data.value.host.memory_percent);
  return +Math.min(raw, remaining).toFixed(1);
});

const showFeedback = (type: 'success' | 'error', text: string) => {
  feedbackMsg.value = { type, text };
  setTimeout(() => {
    if (feedbackMsg.value?.text === text) feedbackMsg.value = null;
  }, 6000);
};

const handlePrune = async (target: 'all' | 'images' | 'containers' | 'volumes') => {
  const labels: Record<string, string> = {
    all: 'todos os recursos Docker não utilizados (imagens, contêineres parados, volumes e redes)',
    images: 'todas as imagens Docker não utilizadas por nenhum contêiner',
    containers: 'todos os contêineres parados',
    volumes: 'todos os volumes locais não montados',
  };
  if (!confirm(`Confirmar limpeza de ${labels[target]}?`)) return;

  pruningTarget.value = target;
  try {
    const res = await api.system.prune(target);
    showFeedback(
      'success',
      `Limpeza concluída (${res.space_reclaimed_mb.toFixed(2)} MB liberados • ${res.images_deleted} imagens, ${res.containers_deleted} contêineres, ${res.volumes_deleted} volumes removidos).`
    );
    await loadData(true);
  } catch (err: any) {
    showFeedback('error', `Falha na limpeza: ${err.message || err}`);
  } finally {
    pruningTarget.value = null;
  }
};

const handleDeleteImage = async (id: string, tag: string) => {
  if (!confirm(`Remover imagem "${tag}" (${id})?`)) return;
  deletingId.value = id;
  try {
    await api.system.deleteImage(id);
    showFeedback('success', `Imagem ${tag} removida.`);
    await loadData(true);
  } catch (err: any) {
    showFeedback('error', `Não foi possível remover a imagem: ${err.message || err}`);
  } finally {
    deletingId.value = null;
  }
};

const handleDeleteVolume = async (name: string) => {
  if (!confirm(`Remover volume "${name}" permanentemente?`)) return;
  deletingId.value = name;
  try {
    await api.system.deleteVolume(name);
    showFeedback('success', `Volume ${name} removido.`);
    await loadData(true);
  } catch (err: any) {
    showFeedback('error', `Não foi possível remover o volume: ${err.message || err}`);
  } finally {
    deletingId.value = null;
  }
};

// Backup & Restore de Volumes Docker
const backingUpVolume = ref<string | null>(null);
const showRestorePanel = ref(false);
const restoreVolumeName = ref('');
const restoringVolume = ref(false);
const restoreInputRef = ref<HTMLInputElement | null>(null);

const handleBackupVolume = async (name: string) => {
  backingUpVolume.value = name;
  try {
    await api.system.backupVolume(name);
    showFeedback('success', `Backup do volume "${name}" (.tar.gz) exportado com sucesso!`);
  } catch (err: any) {
    showFeedback('error', `Falha ao exportar backup do volume: ${err.message || err}`);
  } finally {
    backingUpVolume.value = null;
  }
};

const triggerRestoreFile = (volName?: string) => {
  if (volName) {
    restoreVolumeName.value = volName;
  }
  showRestorePanel.value = true;
};

const onRestoreFileSelected = async (ev: Event) => {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  const targetVol = restoreVolumeName.value.trim();
  if (!file) return;
  if (!targetVol) {
    alert('Informe o nome do volume de destino para restaurar o backup.');
    input.value = '';
    return;
  }

  restoringVolume.value = true;
  const reader = new FileReader();
  reader.onload = async () => {
    const resStr = String(reader.result || '');
    const base64 = resStr.includes(',') ? (resStr.split(',')[1] || '') : resStr;
    try {
      const res = await api.system.restoreVolume(targetVol, base64);
      showFeedback(
        'success',
        `Backup restaurado com sucesso no volume "${res.volume}" (${(res.restored_bytes / 1024).toFixed(1)} KB extraídos).`
      );
      showRestorePanel.value = false;
      await loadData(true);
    } catch (err: any) {
      showFeedback('error', `Falha ao restaurar volume: ${err.message || err}`);
    } finally {
      restoringVolume.value = false;
      input.value = '';
    }
  };
  reader.readAsDataURL(file);
};
</script>

<template>
  <div class="space-y-6">
    <!-- Barra Superior de Telemetria do Host -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-dock-border">
      <div>
        <div class="flex items-center gap-2.5">
          <h2 class="text-lg font-semibold text-dock-text tracking-tight">Monitor de Recursos & Armazenamento</h2>
          <span
            v-if="data"
            class="font-mono text-[11px] px-2 py-0.5 rounded bg-dock-surface border border-dock-border text-dock-text-muted"
          >
            host: {{ data.host.hostname }}
          </span>
        </div>
        <p v-if="data" class="text-xs text-dock-text-dim font-mono mt-1">
          {{ data.host.cpu_model }} ({{ data.host.cpu_cores }} threads) • {{ data.host.os }} • Uptime: {{ formatUptime(data.host.uptime_seconds) }} • Load: {{ data.host.load_avg.join(' / ') }}
        </p>
      </div>

      <div class="flex items-center gap-2 self-start lg:self-auto">
        <button
          @click="toggleAutoRefresh"
          class="px-2.5 py-1.5 rounded text-xs font-mono border transition-colors cursor-pointer flex items-center gap-2"
          :class="
            autoRefresh
              ? 'bg-dock-surface border-dock-border-light text-dock-text'
              : 'bg-dock-bg border-dock-border text-dock-text-dim hover:text-dock-text'
          "
        >
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="autoRefresh ? 'bg-dock-success' : 'bg-dock-text-dim'"
          ></span>
          {{ autoRefresh ? 'Tempo real (4s)' : 'Pausado' }}
        </button>

        <button
          @click="loadData(true)"
          :disabled="refreshing"
          class="px-2.5 py-1.5 rounded text-xs font-medium bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text-muted hover:text-dock-text transition-colors flex items-center gap-1.5 cursor-pointer"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': refreshing }" />
          Atualizar
        </button>
      </div>
    </div>

    <!-- Banner de retorno de operação -->
    <div
      v-if="feedbackMsg"
      class="px-4 py-2.5 rounded border text-xs font-mono flex items-center justify-between"
      :class="
        feedbackMsg.type === 'success'
          ? 'bg-dock-success/10 border-dock-success/30 text-dock-success'
          : 'bg-dock-error/10 border-dock-error/30 text-dock-error'
      "
    >
      <div class="flex items-center gap-2">
        <CheckCircle2 v-if="feedbackMsg.type === 'success'" class="w-4 h-4 shrink-0" />
        <AlertTriangle v-else class="w-4 h-4 shrink-0" />
        <span>{{ feedbackMsg.text }}</span>
      </div>
      <button @click="feedbackMsg = null" class="text-xs underline ml-4 cursor-pointer">fechar</button>
    </div>

    <div v-if="loading && !data" class="flex justify-center py-20">
      <LoadingSpinner />
    </div>

    <template v-else-if="data">
      <!-- SEÇÃO 1: USO REAL DO COMPUTADOR VS DOCKER (CPU & RAM) -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Card 1: Processamento (CPU) -->
        <div class="glass-panel p-5 flex flex-col justify-between space-y-4">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <Cpu class="w-4 h-4 text-dock-text-muted" />
                <span class="text-xs font-semibold uppercase tracking-wider text-dock-text-muted">
                  Processamento (CPU Real vs. Docker)
                </span>
              </div>
              <span class="text-xs font-mono text-dock-text-dim">
                {{ data.host.cpu_cores }} núcleos lógicos
              </span>
            </div>

            <!-- Números Principais -->
            <div class="grid grid-cols-3 gap-3 py-3 border-y border-dock-border font-mono">
              <div>
                <div class="text-[11px] text-dock-text-dim">Uso Real (Host)</div>
                <div class="text-xl font-semibold text-dock-text tabular-nums mt-0.5">
                  {{ data.host.cpu_percent.toFixed(1) }}%
                </div>
              </div>
              <div class="border-l border-dock-border pl-3">
                <div class="text-[11px] text-dock-text-dim">Puxado pelo Docker</div>
                <div class="text-xl font-semibold text-dock-accent tabular-nums mt-0.5">
                  {{ data.docker_usage.cpu_percent.toFixed(2) }}%
                  <span class="text-[11px] font-normal text-dock-text-dim">
                    ({{ data.docker_usage.cpu_normalized_percent }}% host)
                  </span>
                </div>
              </div>
              <div class="border-l border-dock-border pl-3">
                <div class="text-[11px] text-dock-text-dim">Outros Processos SO</div>
                <div class="text-xl font-semibold text-dock-text-muted tabular-nums mt-0.5">
                  {{ nonDockerCpuPercent.toFixed(1) }}%
                </div>
              </div>
            </div>

            <!-- Barra Empilhada CPU -->
            <div class="mt-3 space-y-1.5">
              <div class="h-2.5 w-full bg-dock-bg rounded-sm overflow-hidden border border-dock-border flex">
                <div
                  class="bg-dock-accent transition-all duration-300"
                  :style="{ width: `${Math.min(100, data.docker_usage.cpu_normalized_percent)}%` }"
                  title="Docker Engine"
                ></div>
                <div
                  class="bg-dock-text-muted/60 transition-all duration-300"
                  :style="{ width: `${Math.min(100, nonDockerCpuPercent)}%` }"
                  title="Sistema Operacional / Outros Processos"
                ></div>
              </div>
              <div class="flex items-center justify-between text-[11px] font-mono text-dock-text-dim">
                <div class="flex items-center gap-3">
                  <span class="inline-flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-dock-accent"></span> Docker ({{ data.docker_usage.cpu_normalized_percent }}%)
                  </span>
                  <span class="inline-flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-dock-text-muted/60"></span> Host/SO ({{ nonDockerCpuPercent }}%)
                  </span>
                </div>
                <span>Livre: {{ Math.max(0, 100 - data.host.cpu_percent).toFixed(1) }}%</span>
              </div>
            </div>
          </div>

          <!-- Grade de uso por núcleo -->
          <div v-if="data.host.cpu_per_core.length" class="pt-2 border-t border-dock-border">
            <div class="text-[11px] font-mono text-dock-text-dim mb-2">Carga individual por thread (vCPU)</div>
            <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
              <div
                v-for="(pct, idx) in data.host.cpu_per_core"
                :key="idx"
                class="bg-dock-bg border border-dock-border rounded px-2 py-1.5"
              >
                <div class="flex justify-between text-[10px] font-mono">
                  <span class="text-dock-text-dim">C{{ idx }}</span>
                  <span class="text-dock-text tabular-nums">{{ pct.toFixed(0) }}%</span>
                </div>
                <div class="h-1 bg-dock-surface rounded-xs overflow-hidden mt-1">
                  <div
                    class="h-full transition-all duration-300"
                    :class="pct > 80 ? 'bg-dock-error' : pct > 50 ? 'bg-dock-warning' : 'bg-dock-accent'"
                    :style="{ width: `${Math.min(100, pct)}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Card 2: Memória Física (RAM & Swap) -->
        <div class="glass-panel p-5 flex flex-col justify-between space-y-4">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <Server class="w-4 h-4 text-dock-text-muted" />
                <span class="text-xs font-semibold uppercase tracking-wider text-dock-text-muted">
                  Memória Física (RAM do Computador vs. Docker)
                </span>
              </div>
              <span class="text-xs font-mono text-dock-text-dim">
                Total: {{ formatSizeMb(data.host.memory_total_mb) }}
              </span>
            </div>

            <!-- Números Principais -->
            <div class="grid grid-cols-3 gap-3 py-3 border-y border-dock-border font-mono">
              <div>
                <div class="text-[11px] text-dock-text-dim">Uso Real (Host)</div>
                <div class="text-xl font-semibold text-dock-text tabular-nums mt-0.5">
                  {{ formatSizeMb(data.host.memory_used_mb) }}
                  <span class="text-[11px] font-normal text-dock-text-dim">({{ data.host.memory_percent }}%)</span>
                </div>
              </div>
              <div class="border-l border-dock-border pl-3">
                <div class="text-[11px] text-dock-text-dim">Puxado pelo Docker</div>
                <div class="text-xl font-semibold text-dock-accent tabular-nums mt-0.5">
                  {{ formatSizeMb(data.docker_usage.memory_used_mb) }}
                  <span class="text-[11px] font-normal text-dock-text-dim">
                    ({{ data.docker_usage.memory_share_of_host_percent }}%)
                  </span>
                </div>
              </div>
              <div class="border-l border-dock-border pl-3">
                <div class="text-[11px] text-dock-text-dim">Livre / Disponível</div>
                <div class="text-xl font-semibold text-dock-text-muted tabular-nums mt-0.5">
                  {{ formatSizeMb(data.host.memory_free_mb) }}
                </div>
              </div>
            </div>

            <!-- Barra Empilhada RAM -->
            <div class="mt-3 space-y-1.5">
              <div class="h-2.5 w-full bg-dock-bg rounded-sm overflow-hidden border border-dock-border flex">
                <div
                  class="bg-dock-accent transition-all duration-300"
                  :style="{ width: `${Math.min(100, data.docker_usage.memory_share_of_host_percent)}%` }"
                  title="Alocado pelos Contêineres Docker"
                ></div>
                <div
                  class="bg-dock-text-muted/60 transition-all duration-300"
                  :style="{ width: `${Math.min(100, nonDockerMemPercent)}%` }"
                  title="Outros Processos do Computador"
                ></div>
                <div
                  class="bg-dock-border-light transition-all duration-300"
                  :style="{ width: `${Math.min(100, cachedMemPercent)}%` }"
                  title="Cache / Buffers de Disco do Kernel"
                ></div>
              </div>
              <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-dock-text-dim">
                <div class="flex flex-wrap items-center gap-3">
                  <span class="inline-flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-dock-accent"></span> Docker ({{ formatSizeMb(data.docker_usage.memory_used_mb) }})
                  </span>
                  <span class="inline-flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-dock-text-muted/60"></span> SO/Processos ({{ formatSizeMb(Math.max(0, data.host.memory_used_mb - data.docker_usage.memory_used_mb)) }})
                  </span>
                  <span class="inline-flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-dock-border-light"></span> Cache/Buffers ({{ formatSizeMb(data.host.memory_cached_mb) }})
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Rodapé de Memória: Swap e Tráfego de Rede Docker -->
          <div class="pt-3 border-t border-dock-border grid grid-cols-2 gap-3 text-xs font-mono">
            <div class="bg-dock-bg border border-dock-border rounded px-3 py-2 flex items-center justify-between">
              <span class="text-dock-text-dim">Swap do Sistema</span>
              <span class="text-dock-text tabular-nums">
                {{ formatSizeMb(data.host.swap_used_mb) }} / {{ formatSizeMb(data.host.swap_total_mb) }} ({{ data.host.swap_percent }}%)
              </span>
            </div>
            <div class="bg-dock-bg border border-dock-border rounded px-3 py-2 flex items-center justify-between">
              <span class="text-dock-text-dim">I/O Rede Docker</span>
              <span class="text-dock-text tabular-nums">
                ↓ {{ formatSizeMb(data.docker_usage.network_rx_mb) }} • ↑ {{ formatSizeMb(data.docker_usage.network_tx_mb) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- SEÇÃO 2: CONSUMO POR CONTÊINER DOCKER -->
      <div class="glass-panel overflow-hidden">
        <div class="px-5 py-3.5 border-b border-dock-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <Box class="w-4 h-4 text-dock-text-muted" />
            <h3 class="text-sm font-semibold text-dock-text">
              Recursos Puxados por Contêiner ({{ data.docker_usage.containers_running }} ativos de {{ data.docker_usage.containers_total }})
            </h3>
          </div>
          <span class="text-xs font-mono text-dock-text-dim">
            Clique em um contêiner para inspecionar logs e variáveis
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-dock-border bg-dock-surface text-dock-text-dim font-mono uppercase text-[11px]">
                <th class="px-4 py-2.5 font-medium">Contêiner</th>
                <th class="px-4 py-2.5 font-medium">Status</th>
                <th class="px-4 py-2.5 font-medium">Imagem</th>
                <th class="px-4 py-2.5 font-medium">CPU</th>
                <th class="px-4 py-2.5 font-medium">Memória RAM (% Host)</th>
                <th class="px-4 py-2.5 font-medium">Rede (RX / TX)</th>
                <th class="px-4 py-2.5 font-medium text-right">Camada Disco (R/W)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-dock-border font-mono">
              <tr
                v-for="c in data.docker_usage.containers"
                :key="c.id"
                @click="router.push(`/containers/${c.id}`)"
                class="hover:bg-dock-surface/70 transition-colors cursor-pointer"
              >
                <td class="px-4 py-3 font-sans font-medium text-dock-text">
                  {{ c.name }}
                  <span class="block text-[10px] font-mono text-dock-text-dim">{{ c.id }}</span>
                </td>
                <td class="px-4 py-3 font-sans">
                  <StatusBadge :status="c.state" size="sm" />
                </td>
                <td class="px-4 py-3 text-dock-text-muted max-w-[200px] truncate" :title="c.image">
                  {{ c.image }}
                </td>
                <td class="px-4 py-3 w-36">
                  <div class="flex justify-between text-dock-text tabular-nums mb-1">
                    <span>{{ c.cpu_percent.toFixed(2) }}%</span>
                  </div>
                  <div class="h-1.5 bg-dock-bg rounded-xs overflow-hidden border border-dock-border">
                    <div
                      class="h-full bg-dock-accent transition-all duration-300"
                      :style="{ width: `${Math.min(100, c.cpu_percent)}%` }"
                    ></div>
                  </div>
                </td>
                <td class="px-4 py-3 w-48">
                  <div class="flex justify-between tabular-nums mb-1">
                    <span class="text-dock-text">{{ formatSizeMb(c.memory_usage_mb) }}</span>
                    <span class="text-dock-text-dim">{{ c.memory_host_percent.toFixed(1) }}%</span>
                  </div>
                  <div class="h-1.5 bg-dock-bg rounded-xs overflow-hidden border border-dock-border">
                    <div
                      class="h-full bg-dock-success transition-all duration-300"
                      :style="{ width: `${Math.min(100, c.memory_host_percent * 4)}%` }"
                    ></div>
                  </div>
                </td>
                <td class="px-4 py-3 text-dock-text-muted tabular-nums whitespace-nowrap">
                  ↓ {{ formatSizeMb(c.network_rx_mb) }} / ↑ {{ formatSizeMb(c.network_tx_mb) }}
                </td>
                <td class="px-4 py-3 text-right tabular-nums text-dock-text-muted whitespace-nowrap">
                  <span class="text-dock-text">{{ formatSizeMb(c.size_rw_mb) }}</span>
                  <span v-if="c.size_rootfs_mb > 0" class="text-dock-text-dim text-[11px] block">
                    rootfs: {{ formatSizeMb(c.size_rootfs_mb) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- SEÇÃO 3: GERENCIAMENTO DE ESPAÇO EM DISCO (PARTIÇÕES HOST + DOCKER STORAGE) -->
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2">
          <div>
            <h3 class="text-base font-semibold text-dock-text flex items-center gap-2">
              <HardDrive class="w-4 h-4 text-dock-text-muted" />
              Gerenciamento de Espaço em Disco
            </h3>
            <p class="text-xs text-dock-text-dim mt-0.5">
              Ocupação física das partições do computador e detalhamento de armazenamento do Docker Engine
            </p>
          </div>

          <button
            @click="handlePrune('all')"
            :disabled="pruningTarget !== null"
            class="px-3 py-1.5 rounded text-xs font-medium bg-dock-surface hover:bg-dock-error/15 text-dock-text hover:text-dock-error border border-dock-border hover:border-dock-error/40 transition-colors flex items-center gap-2 cursor-pointer self-start sm:self-auto"
          >
            <Trash2 class="w-3.5 h-3.5" />
            <span>
              {{
                pruningTarget === 'all'
                  ? 'Executando limpeza...'
                  : `Limpar Tudo Não Utilizado (${formatSizeMb(data.storage.reclaimable_mb)} recuperáveis)`
              }}
            </span>
          </button>
        </div>

        <!-- 3A: Partições Físicas e Virtuais do Computador -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            v-for="disk in data.host.disks"
            :key="disk.mount"
            class="glass-panel p-4 space-y-3"
          >
            <div class="flex items-start justify-between gap-2">
              <div>
                <div class="text-xs font-semibold text-dock-text">{{ disk.label }}</div>
                <div class="text-[11px] font-mono text-dock-text-dim">mount: {{ disk.mount }}</div>
              </div>
              <span
                class="font-mono text-xs font-semibold px-2 py-0.5 rounded border tabular-nums"
                :class="
                  disk.percent >= 90
                    ? 'bg-dock-error/10 text-dock-error border-dock-error/30'
                    : disk.percent >= 75
                    ? 'bg-dock-warning/10 text-dock-warning border-dock-warning/30'
                    : 'bg-dock-surface text-dock-text-muted border-dock-border'
                "
              >
                {{ disk.percent.toFixed(1) }}%
              </span>
            </div>

            <div class="h-2 w-full bg-dock-bg rounded-xs overflow-hidden border border-dock-border">
              <div
                class="h-full transition-all duration-300"
                :class="
                  disk.percent >= 90
                    ? 'bg-dock-error'
                    : disk.percent >= 75
                    ? 'bg-dock-warning'
                    : 'bg-dock-accent'
                "
                :style="{ width: `${Math.min(100, disk.percent)}%` }"
              ></div>
            </div>

            <div class="flex justify-between text-xs font-mono text-dock-text-dim tabular-nums">
              <span>Usado: <strong class="text-dock-text">{{ disk.used_gb }} GB</strong></span>
              <span>Livre: <strong class="text-dock-text">{{ disk.free_gb }} GB</strong></span>
              <span>Total: {{ disk.total_gb }} GB</span>
            </div>
          </div>
        </div>

        <!-- 3B: Categorias de Armazenamento Docker -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- Imagens -->
          <div class="glass-panel p-4 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between text-xs text-dock-text-muted mb-1">
                <span class="font-medium flex items-center gap-1.5">
                  <Layers class="w-3.5 h-3.5" /> Imagens Docker
                </span>
                <span class="font-mono text-[11px]">
                  {{ data.storage.categories.images.active_count }}/{{ data.storage.categories.images.total_count }} ativas
                </span>
              </div>
              <div class="text-xl font-mono font-semibold text-dock-text tabular-nums">
                {{ formatSizeMb(data.storage.categories.images.size_mb) }}
              </div>
              <div class="text-[11px] font-mono text-dock-text-dim mt-1">
                Recuperável: {{ formatSizeMb(data.storage.categories.images.reclaimable_mb) }}
              </div>
            </div>
            <button
              @click="handlePrune('images')"
              :disabled="pruningTarget !== null || data.storage.categories.images.reclaimable_mb <= 0"
              class="w-full py-1.5 px-2.5 rounded text-xs font-mono border border-dock-border bg-dock-surface hover:bg-dock-panel text-dock-text-muted hover:text-dock-text disabled:opacity-40 transition-colors cursor-pointer"
            >
              Limpar imagens sem uso
            </button>
          </div>

          <!-- Contêineres R/W -->
          <div class="glass-panel p-4 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between text-xs text-dock-text-muted mb-1">
                <span class="font-medium flex items-center gap-1.5">
                  <Box class="w-3.5 h-3.5" /> Camada de Contêineres
                </span>
                <span class="font-mono text-[11px]">
                  {{ data.storage.categories.containers.active_count }}/{{ data.storage.categories.containers.total_count }} ativos
                </span>
              </div>
              <div class="text-xl font-mono font-semibold text-dock-text tabular-nums">
                {{ formatSizeMb(data.storage.categories.containers.size_mb) }}
              </div>
              <div class="text-[11px] font-mono text-dock-text-dim mt-1">
                Parados: {{ data.storage.categories.containers.total_count - data.storage.categories.containers.active_count }} contêineres
              </div>
            </div>
            <button
              @click="handlePrune('containers')"
              :disabled="
                pruningTarget !== null ||
                data.storage.categories.containers.total_count === data.storage.categories.containers.active_count
              "
              class="w-full py-1.5 px-2.5 rounded text-xs font-mono border border-dock-border bg-dock-surface hover:bg-dock-panel text-dock-text-muted hover:text-dock-text disabled:opacity-40 transition-colors cursor-pointer"
            >
              Remover contêineres parados
            </button>
          </div>

          <!-- Volumes Locais -->
          <div class="glass-panel p-4 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between text-xs text-dock-text-muted mb-1">
                <span class="font-medium flex items-center gap-1.5">
                  <Database class="w-3.5 h-3.5" /> Volumes Locais
                </span>
                <span class="font-mono text-[11px]">
                  {{ data.storage.categories.volumes.active_count }}/{{ data.storage.categories.volumes.total_count }} em uso
                </span>
              </div>
              <div class="text-xl font-mono font-semibold text-dock-text tabular-nums">
                {{ formatSizeMb(data.storage.categories.volumes.size_mb) }}
              </div>
              <div class="text-[11px] font-mono text-dock-text-dim mt-1">
                Recuperável: {{ formatSizeMb(data.storage.categories.volumes.reclaimable_mb) }}
              </div>
            </div>
            <button
              @click="handlePrune('volumes')"
              :disabled="
                pruningTarget !== null ||
                data.storage.categories.volumes.total_count === data.storage.categories.volumes.active_count
              "
              class="w-full py-1.5 px-2.5 rounded text-xs font-mono border border-dock-border bg-dock-surface hover:bg-dock-panel text-dock-text-muted hover:text-dock-text disabled:opacity-40 transition-colors cursor-pointer"
            >
              Limpar volumes órfãos
            </button>
          </div>

          <!-- Repositórios Git & Build Cache -->
          <div class="glass-panel p-4 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between text-xs text-dock-text-muted mb-1">
                <span class="font-medium flex items-center gap-1.5">
                  <FolderGit2 class="w-3.5 h-3.5" /> Repositórios & Cache
                </span>
                <span class="font-mono text-[11px]">{{ data.storage.repos_count }} repos</span>
              </div>
              <div class="text-xl font-mono font-semibold text-dock-text tabular-nums">
                {{ formatSizeMb(data.storage.repos_dir_mb + data.storage.categories.build_cache.size_mb) }}
              </div>
              <div class="text-[11px] font-mono text-dock-text-dim mt-1">
                Git clones: {{ formatSizeMb(data.storage.repos_dir_mb) }} • Cache: {{ formatSizeMb(data.storage.categories.build_cache.size_mb) }}
              </div>
            </div>
            <div class="py-1.5 px-2.5 rounded text-[11px] font-mono border border-dock-border bg-dock-bg text-dock-text-dim text-center">
              Total Docker: {{ formatSizeMb(data.storage.total_docker_mb) }}
            </div>
          </div>
        </div>

        <!-- 3C: Inspeção e Exclusão Individual de Imagens e Volumes -->
        <div class="glass-panel overflow-hidden">
          <div class="px-5 py-3 border-b border-dock-border flex items-center justify-between">
            <div class="flex items-center gap-2">
              <button
                @click="activeStorageTab = 'images'"
                class="px-3 py-1.5 rounded text-xs font-medium transition-colors cursor-pointer"
                :class="
                  activeStorageTab === 'images'
                    ? 'bg-dock-surface text-dock-text border border-dock-border-light'
                    : 'text-dock-text-muted hover:text-dock-text'
                "
              >
                Imagens no Disco ({{ data.storage.images_list.length }})
              </button>
              <button
                @click="activeStorageTab = 'volumes'"
                class="px-3 py-1.5 rounded text-xs font-medium transition-colors cursor-pointer"
                :class="
                  activeStorageTab === 'volumes'
                    ? 'bg-dock-surface text-dock-text border border-dock-border-light'
                    : 'text-dock-text-muted hover:text-dock-text'
                "
              >
                Volumes Docker ({{ data.storage.volumes_list.length }})
              </button>
            </div>
            <span class="text-xs font-mono text-dock-text-dim hidden sm:inline">
              Ordenado por espaço ocupado
            </span>
          </div>

          <!-- Aba Imagens -->
          <div v-if="activeStorageTab === 'images'" class="overflow-x-auto">
            <table class="w-full text-left text-xs border-collapse font-mono">
              <thead>
                <tr class="border-b border-dock-border bg-dock-surface text-dock-text-dim uppercase text-[11px]">
                  <th class="px-4 py-2.5 font-medium">Tag / Repositório</th>
                  <th class="px-4 py-2.5 font-medium">ID da Imagem</th>
                  <th class="px-4 py-2.5 font-medium">Status de Uso</th>
                  <th class="px-4 py-2.5 font-medium">Camada Compartilhada</th>
                  <th class="px-4 py-2.5 font-medium">Tamanho Total</th>
                  <th class="px-4 py-2.5 font-medium text-right">Ação</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-dock-border">
                <tr
                  v-for="img in data.storage.images_list"
                  :key="img.id"
                  class="hover:bg-dock-surface/60 transition-colors"
                >
                  <td class="px-4 py-2.5 text-dock-text font-medium">{{ img.tag }}</td>
                  <td class="px-4 py-2.5 text-dock-text-dim">{{ img.id }}</td>
                  <td class="px-4 py-2.5 font-sans">
                    <span
                      class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] border"
                      :class="
                        img.in_use
                          ? 'bg-dock-success/10 text-dock-success border-dock-success/30'
                          : 'bg-dock-warning/10 text-dock-warning border-dock-warning/30'
                      "
                    >
                      {{ img.in_use ? `Em uso (${img.containers_count})` : 'Sem uso (recuperável)' }}
                    </span>
                  </td>
                  <td class="px-4 py-2.5 text-dock-text-dim tabular-nums">
                    {{ formatSizeMb(img.shared_mb) }}
                  </td>
                  <td class="px-4 py-2.5 text-dock-text font-semibold tabular-nums">
                    {{ formatSizeMb(img.size_mb) }}
                  </td>
                  <td class="px-4 py-2.5 text-right">
                    <button
                      @click="handleDeleteImage(img.id, img.tag)"
                      :disabled="img.in_use || deletingId === img.id"
                      class="px-2.5 py-1 rounded text-[11px] font-sans border border-dock-border bg-dock-surface hover:bg-dock-error/15 hover:text-dock-error hover:border-dock-error/30 text-dock-text-muted disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer"
                      :title="img.in_use ? 'Imagem em uso por contêiner ativo' : 'Remover imagem do disco'"
                    >
                      Remover
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Aba Volumes -->
          <div v-else class="space-y-3">
            <input
              ref="restoreInputRef"
              type="file"
              accept=".tar,.gz,.tgz"
              class="hidden"
              @change="onRestoreFileSelected"
            />

            <div class="px-4 pt-3 flex flex-wrap items-center justify-between gap-2">
              <p class="text-xs text-dock-text-dim">
                Exporte qualquer volume em <code class="text-dock-accent">.tar.gz</code> ou restaure dados de um arquivo de backup em 1 clique.
              </p>
              <button
                @click="showRestorePanel = !showRestorePanel"
                class="px-3 py-1.5 rounded text-xs font-medium bg-dock-accent hover:bg-dock-accent-hover text-white flex items-center gap-1.5 cursor-pointer"
              >
                <Upload class="w-3.5 h-3.5" /> Restaurar Backup em Volume (.tar.gz)
              </button>
            </div>

            <div
              v-if="showRestorePanel"
              class="mx-4 p-3.5 rounded bg-dock-bg border border-dock-accent/40 flex flex-col sm:flex-row sm:items-center gap-3 text-xs"
            >
              <div class="flex-1">
                <label class="block text-dock-text-muted mb-1">
                  Nome do Volume de Destino (existente ou novo volume a criar):
                </label>
                <input
                  v-model="restoreVolumeName"
                  type="text"
                  placeholder="Ex: deploydock_pgdata ou meu_volume_backup"
                  class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-3 py-1.5 font-mono text-dock-text outline-none"
                />
              </div>
              <div class="flex items-center gap-2 self-end">
                <button
                  @click="restoreInputRef?.click()"
                  :disabled="restoringVolume || !restoreVolumeName.trim()"
                  class="px-3.5 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Upload class="w-3.5 h-3.5" />
                  {{ restoringVolume ? 'Restaurando...' : 'Escolher Arquivo .tar.gz e Restaurar' }}
                </button>
                <button
                  @click="showRestorePanel = false"
                  class="px-2.5 py-1.5 text-dock-text-dim hover:text-dock-text cursor-pointer"
                >
                  Cancelar
                </button>
              </div>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs border-collapse font-mono">
                <thead>
                  <tr class="border-b border-dock-border bg-dock-surface text-dock-text-dim uppercase text-[11px]">
                    <th class="px-4 py-2.5 font-medium">Nome do Volume</th>
                    <th class="px-4 py-2.5 font-medium">Driver</th>
                    <th class="px-4 py-2.5 font-medium">Status</th>
                    <th class="px-4 py-2.5 font-medium">Tamanho</th>
                    <th class="px-4 py-2.5 font-medium text-right">Backup & Ações</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-dock-border">
                  <tr
                    v-for="vol in data.storage.volumes_list"
                    :key="vol.name"
                    class="hover:bg-dock-surface/60 transition-colors"
                  >
                    <td class="px-4 py-2.5 text-dock-text font-medium">{{ vol.name }}</td>
                    <td class="px-4 py-2.5 text-dock-text-dim">{{ vol.driver }}</td>
                    <td class="px-4 py-2.5 font-sans">
                      <span
                        class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] border"
                        :class="
                          vol.in_use
                            ? 'bg-dock-success/10 text-dock-success border-dock-success/30'
                            : 'bg-dock-warning/10 text-dock-warning border-dock-warning/30'
                        "
                      >
                        {{ vol.in_use ? `Montado (${vol.ref_count})` : 'Órfão (recuperável)' }}
                      </span>
                    </td>
                    <td class="px-4 py-2.5 text-dock-text font-semibold tabular-nums">
                      {{ formatSizeMb(vol.size_mb) }}
                    </td>
                    <td class="px-4 py-2.5 text-right whitespace-nowrap">
                      <div class="inline-flex items-center gap-1.5 font-sans">
                        <button
                          @click="handleBackupVolume(vol.name)"
                          :disabled="backingUpVolume === vol.name"
                          class="px-2.5 py-1 rounded text-[11px] border border-dock-accent/40 bg-dock-accent/10 hover:bg-dock-accent/20 text-dock-accent transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
                          title="Exportar backup completo deste volume em .tar.gz"
                        >
                          <Download class="w-3 h-3" />
                          {{ backingUpVolume === vol.name ? 'Gerando...' : 'Backup .tar.gz' }}
                        </button>
                        <button
                          @click="triggerRestoreFile(vol.name)"
                          class="px-2 py-1 rounded text-[11px] border border-dock-border bg-dock-surface hover:bg-dock-panel text-dock-text-muted hover:text-dock-text transition-colors flex items-center gap-1 cursor-pointer"
                          title="Restaurar arquivo .tar.gz para dentro deste volume"
                        >
                          <Upload class="w-3 h-3" /> Restaurar
                        </button>
                        <button
                          @click="handleDeleteVolume(vol.name)"
                          :disabled="vol.in_use || deletingId === vol.name"
                          class="px-2.5 py-1 rounded text-[11px] border border-dock-border bg-dock-surface hover:bg-dock-error/15 hover:text-dock-error hover:border-dock-error/30 text-dock-text-muted disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer"
                          :title="vol.in_use ? 'Volume montado em contêiner' : 'Remover volume'"
                        >
                          Remover
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
