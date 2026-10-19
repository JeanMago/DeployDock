<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue';
import {
  Search,
  Trash2,
  Download,
  Copy,
  RefreshCw,
  Pause,
  Play,
  Clock,
  WrapText,
  Maximize2,
  Minimize2,
  Check,
} from 'lucide-vue-next';
import { useWebSocket } from '@/composables/useWebSocket';
import { api } from '@/services/api';

const props = defineProps<{ containerId: string }>();

interface ParsedLogLine {
  id: number;
  raw: string;
  timestamp: string | null;
  message: string;
  level: 'error' | 'warn' | 'info';
}

const rawLines = ref<string[]>([]);
const searchQuery = ref('');
const levelFilter = ref<'all' | 'error' | 'warn'>('all');
const tailCount = ref<number>(250);
const sinceSeconds = ref<number>(0);
const showTimestamps = ref(true);
const wordWrap = ref(true);
const autoScroll = ref(true);
const isPaused = ref(false);
const isFullscreen = ref(false);
const loading = ref(false);
const copied = ref(false);
const logContainerRef = ref<HTMLElement | null>(null);

let lineCounter = 0;

// Regex para separar timestamp ISO-8601 no início da linha do Docker
const TS_REGEX = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+(.*)$/;

const detectLevel = (msg: string): 'error' | 'warn' | 'info' => {
  const lower = msg.toLowerCase();
  if (
    lower.includes('error') ||
    lower.includes('err ') ||
    lower.includes('[emerg]') ||
    lower.includes('[crit]') ||
    lower.includes('[alert]') ||
    lower.includes('exception') ||
    lower.includes('traceback') ||
    lower.includes('fatal') ||
    /"\s+5\d{2}\s+/.test(msg)
  ) {
    return 'error';
  }
  if (
    lower.includes('warn') ||
    lower.includes('[warn]') ||
    lower.includes('deprecated') ||
    /"\s+4\d{2}\s+/.test(msg)
  ) {
    return 'warn';
  }
  return 'info';
};

const formatIsoTime = (iso: string): string => {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso.slice(11, 19);
    return d.toLocaleTimeString('pt-BR', { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0');
  } catch {
    return iso.slice(11, 19);
  }
};

const parsedLines = computed<ParsedLogLine[]>(() => {
  return rawLines.value.map((raw, idx) => {
    const m = raw.match(TS_REGEX);
    const ts = m ? formatIsoTime(m[1]) : null;
    const message = m ? m[2] : raw;
    return {
      id: idx + 1,
      raw,
      timestamp: ts,
      message,
      level: detectLevel(message),
    };
  });
});

const filteredLines = computed<ParsedLogLine[]>(() => {
  const q = searchQuery.value.trim().toLowerCase();
  return parsedLines.value.filter((item) => {
    if (levelFilter.value !== 'all' && item.level !== levelFilter.value) {
      return false;
    }
    if (q && !item.raw.toLowerCase().includes(q)) {
      return false;
    }
    return true;
  });
});

const counts = computed(() => {
  let errors = 0;
  let warns = 0;
  for (const l of parsedLines.value) {
    if (l.level === 'error') errors++;
    else if (l.level === 'warn') warns++;
  }
  return { total: parsedLines.value.length, errors, warns };
});

const scrollToBottom = () => {
  if (!autoScroll.value || !logContainerRef.value) return;
  nextTick(() => {
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight;
    }
  });
};

const appendIncomingLine = (line: string) => {
  if (isPaused.value || !line) return;
  const subLines = line.split(/\r?\n/).filter((s) => s.trim().length > 0);
  if (!subLines.length) return;
  rawLines.value.push(...subLines);
  if (rawLines.value.length > 5000) {
    rawLines.value.splice(0, rawLines.value.length - 5000);
  }
  lineCounter += subLines.length;
  scrollToBottom();
};

const { status } = useWebSocket(`/ws/containers/${props.containerId}/logs`, (payload: any) => {
  if (!payload) return;
  if (typeof payload === 'string') {
    appendIncomingLine(payload);
  } else if (typeof payload === 'object' && typeof payload.data === 'string') {
    appendIncomingLine(payload.data);
  }
});

const loadHistory = async () => {
  loading.value = true;
  try {
    const res = await api.containers.getLogs(props.containerId, {
      tail: tailCount.value,
      timestamps: true,
      since_seconds: sinceSeconds.value > 0 ? sinceSeconds.value : undefined,
    });
    if (Array.isArray(res)) {
      rawLines.value = res;
    } else if (res && Array.isArray(res.lines)) {
      rawLines.value = res.lines;
    } else if (res && typeof res.logs === 'string') {
      rawLines.value = res.logs.split(/\r?\n/).filter(Boolean);
    } else {
      rawLines.value = [];
    }
    scrollToBottom();
  } catch (e) {
    console.error('Erro ao buscar logs:', e);
  } finally {
    loading.value = false;
  }
};

watch([tailCount, sinceSeconds], () => {
  loadHistory();
});

onMounted(() => {
  loadHistory();
});

const clearLogs = () => {
  rawLines.value = [];
};

const copyLogs = async () => {
  const text = filteredLines.value
    .map((l) => (showTimestamps.value && l.timestamp ? `${l.timestamp} ${l.message}` : l.message))
    .join('\n');
  try {
    await navigator.clipboard.writeText(text);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    // ignore
  }
};

const downloadLogs = () => {
  const text = filteredLines.value
    .map((l) => (l.timestamp ? `${l.timestamp} ${l.message}` : l.message))
    .join('\n');
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `container-${props.containerId.slice(0, 8)}-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.log`;
  a.click();
  URL.revokeObjectURL(url);
};

const handleScroll = () => {
  if (!logContainerRef.value) return;
  const el = logContainerRef.value;
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  autoScroll.value = atBottom;
};
</script>

<template>
  <div
    :class="[
      'glass-panel flex flex-col overflow-hidden border border-dock-border bg-dock-bg',
      isFullscreen ? 'fixed inset-2 z-50 h-auto shadow-2xl' : 'h-[520px] sm:h-[600px]',
    ]"
  >
    <!-- Barra de Ferramentas Responsiva -->
    <div class="p-2.5 bg-dock-surface border-b border-dock-border flex flex-col gap-2">
      <!-- Linha 1: Status, Busca e Filtros de Nível -->
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2 flex-1 min-w-[200px]">
          <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-dock-bg border border-dock-border text-[11px] font-mono shrink-0">
            <span
              class="w-1.5 h-1.5 rounded-full"
              :class="
                isPaused
                  ? 'bg-dock-warning'
                  : status === 'open'
                  ? 'bg-dock-success'
                  : 'bg-dock-text-dim'
              "
            ></span>
            <span class="text-dock-text-muted">
              {{ isPaused ? 'pausado' : status === 'open' ? 'ao vivo' : 'histórico' }}
            </span>
          </div>

          <div class="relative flex-1 max-w-xs">
            <Search class="w-3.5 h-3.5 text-dock-text-dim absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Filtrar linhas de log..."
              class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded pl-8 pr-2.5 py-1 text-xs font-mono text-dock-text placeholder-dock-text-dim outline-none"
            />
          </div>
        </div>

        <!-- Filtros rápidos por nível -->
        <div class="flex flex-wrap items-center gap-1.5 text-[11px] font-mono">
          <button
            @click="levelFilter = 'all'"
            class="px-2 py-1 rounded border transition-colors cursor-pointer"
            :class="
              levelFilter === 'all'
                ? 'bg-dock-panel text-dock-text border-dock-border-light'
                : 'bg-dock-bg text-dock-text-dim border-dock-border hover:text-dock-text'
            "
          >
            Todos ({{ counts.total }})
          </button>
          <button
            @click="levelFilter = 'error'"
            class="px-2 py-1 rounded border transition-colors cursor-pointer"
            :class="
              levelFilter === 'error'
                ? 'bg-dock-error/15 text-dock-error border-dock-error/40'
                : 'bg-dock-bg text-dock-text-dim border-dock-border hover:text-dock-error'
            "
          >
            Erros ({{ counts.errors }})
          </button>
          <button
            @click="levelFilter = 'warn'"
            class="px-2 py-1 rounded border transition-colors cursor-pointer"
            :class="
              levelFilter === 'warn'
                ? 'bg-dock-warning/15 text-dock-warning border-dock-warning/40'
                : 'bg-dock-bg text-dock-text-dim border-dock-border hover:text-dock-warning'
            "
          >
            Avisos ({{ counts.warns }})
          </button>
        </div>
      </div>

      <!-- Linha 2: Controles de Coleta e Ações -->
      <div class="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-dock-border/60 text-xs font-mono">
        <div class="flex flex-wrap items-center gap-1.5">
          <!-- Quantidade de linhas -->
          <select
            v-model.number="tailCount"
            class="bg-dock-bg border border-dock-border rounded px-2 py-1 text-[11px] text-dock-text outline-none cursor-pointer"
            title="Quantidade de linhas carregadas"
          >
            <option :value="100">Últimas 100 linhas</option>
            <option :value="250">Últimas 250 linhas</option>
            <option :value="1000">Últimas 1.000 linhas</option>
            <option :value="5000">Últimas 5.000 linhas</option>
          </select>

          <!-- Janela de tempo -->
          <select
            v-model.number="sinceSeconds"
            class="bg-dock-bg border border-dock-border rounded px-2 py-1 text-[11px] text-dock-text outline-none cursor-pointer"
            title="Período de coleta"
          >
            <option :value="0">Todo o período</option>
            <option :value="300">Últimos 5 min</option>
            <option :value="900">Últimos 15 min</option>
            <option :value="3600">Última 1 hora</option>
            <option :value="86400">Últimas 24 horas</option>
          </select>

          <button
            @click="showTimestamps = !showTimestamps"
            class="px-2 py-1 rounded border text-[11px] flex items-center gap-1 transition-colors cursor-pointer"
            :class="
              showTimestamps
                ? 'bg-dock-panel text-dock-text border-dock-border-light'
                : 'bg-dock-bg text-dock-text-dim border-dock-border'
            "
            title="Exibir ou ocultar horário de cada linha"
          >
            <Clock class="w-3 h-3" />
            <span class="hidden sm:inline">Horário</span>
          </button>

          <button
            @click="wordWrap = !wordWrap"
            class="px-2 py-1 rounded border text-[11px] flex items-center gap-1 transition-colors cursor-pointer"
            :class="
              wordWrap
                ? 'bg-dock-panel text-dock-text border-dock-border-light'
                : 'bg-dock-bg text-dock-text-dim border-dock-border'
            "
            title="Quebra de linha automática"
          >
            <WrapText class="w-3 h-3" />
            <span class="hidden sm:inline">Wrap</span>
          </button>
        </div>

        <div class="flex items-center gap-1.5 ml-auto">
          <button
            @click="isPaused = !isPaused"
            class="px-2 py-1 rounded border border-dock-border bg-dock-bg hover:bg-dock-panel text-dock-text-muted hover:text-dock-text text-[11px] flex items-center gap-1 cursor-pointer"
            :title="isPaused ? 'Retomar stream em tempo real' : 'Pausar stream em tempo real'"
          >
            <Play v-if="isPaused" class="w-3 h-3 text-dock-success" />
            <Pause v-else class="w-3 h-3 text-dock-warning" />
            <span class="hidden sm:inline">{{ isPaused ? 'Retomar' : 'Pausar' }}</span>
          </button>

          <button
            @click="loadHistory"
            class="p-1.5 rounded border border-dock-border bg-dock-bg hover:bg-dock-panel text-dock-text-muted hover:text-dock-text cursor-pointer"
            title="Recarregar histórico de logs"
          >
            <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
          </button>

          <button
            @click="copyLogs"
            class="p-1.5 rounded border border-dock-border bg-dock-bg hover:bg-dock-panel text-dock-text-muted hover:text-dock-text cursor-pointer"
            title="Copiar logs visíveis"
          >
            <Check v-if="copied" class="w-3.5 h-3.5 text-dock-success" />
            <Copy v-else class="w-3.5 h-3.5" />
          </button>

          <button
            @click="downloadLogs"
            class="p-1.5 rounded border border-dock-border bg-dock-bg hover:bg-dock-panel text-dock-text-muted hover:text-dock-text cursor-pointer"
            title="Baixar arquivo .log"
          >
            <Download class="w-3.5 h-3.5" />
          </button>

          <button
            @click="clearLogs"
            class="p-1.5 rounded border border-dock-border bg-dock-bg hover:bg-dock-panel text-dock-text-muted hover:text-dock-error cursor-pointer"
            title="Limpar console"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>

          <button
            @click="isFullscreen = !isFullscreen"
            class="p-1.5 rounded border border-dock-border bg-dock-bg hover:bg-dock-panel text-dock-text-muted hover:text-dock-text cursor-pointer"
            :title="isFullscreen ? 'Sair da tela cheia' : 'Expandir em tela cheia'"
          >
            <Minimize2 v-if="isFullscreen" class="w-3.5 h-3.5" />
            <Maximize2 v-else class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>

    <!-- Área de Saída dos Logs -->
    <div
      ref="logContainerRef"
      @scroll="handleScroll"
      class="flex-1 overflow-y-auto overflow-x-auto p-3 font-mono text-xs leading-relaxed select-text"
    >
      <div v-if="loading && !filteredLines.length" class="text-dock-text-dim py-8 text-center">
        Coletando logs do contêiner...
      </div>
      <div v-else-if="!filteredLines.length" class="text-dock-text-dim py-8 text-center">
        Nenhuma linha de log encontrada para os filtros selecionados.
      </div>
      <div v-else class="space-y-0.5">
        <div
          v-for="item in filteredLines"
          :key="item.id"
          class="flex items-start gap-2.5 px-2 py-0.5 rounded hover:bg-dock-surface/80 border-l-2 transition-colors"
          :class="[
            item.level === 'error'
              ? 'border-dock-error bg-dock-error/5 text-dock-error'
              : item.level === 'warn'
              ? 'border-dock-warning bg-dock-warning/5 text-dock-warning'
              : 'border-transparent text-dock-text',
            wordWrap ? 'whitespace-pre-wrap break-all sm:break-words' : 'whitespace-pre',
          ]"
        >
          <span class="text-[10px] text-dock-text-dim select-none w-8 text-right shrink-0 tabular-nums">
            {{ item.id }}
          </span>
          <span
            v-if="showTimestamps && item.timestamp"
            class="text-[11px] text-dock-text-dim shrink-0 select-none tabular-nums"
          >
            {{ item.timestamp }}
          </span>
          <span class="flex-1 min-w-0">{{ item.message }}</span>
        </div>
      </div>
    </div>

    <!-- Rodapé de Auto-scroll -->
    <div class="px-3 py-1.5 bg-dock-surface border-t border-dock-border flex items-center justify-between text-[11px] font-mono text-dock-text-dim">
      <span>Exibindo {{ filteredLines.length }} de {{ rawLines.length }} linhas</span>
      <button
        @click="
          autoScroll = true;
          scrollToBottom();
        "
        class="hover:text-dock-text cursor-pointer"
        :class="autoScroll ? 'text-dock-success' : 'text-dock-warning underline'"
      >
        {{ autoScroll ? '● Rolagem automática ativa' : '↓ Ir para o final (rolagem pausada)' }}
      </button>
    </div>
  </div>
</template>
