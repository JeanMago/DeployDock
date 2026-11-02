<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { Line } from 'vue-chartjs';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  Legend,
  type ChartOptions,
} from 'chart.js';
import {
  Activity,
  Cpu,
  Server,
  Network,
  HardDrive,
  Layers,
  Pause,
  Play,
  RotateCcw,
  CalendarDays,
  Info,
  Box,
  Filter,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemResourcesOverview, TelemetryHistoryPoint, ContainerTelemetryPoint } from '@/services/types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend);

const props = defineProps<{
  liveOverview?: SystemResourcesOverview | null;
}>();

export type ComponentView = 'all' | 'cpu' | 'ram' | 'network' | 'disk';

const MAX_DAYS = 90;
const STORAGE_KEY_RANGE = 'deploydock.resources.chartRange';
const STORAGE_KEY_CONTAINER = 'deploydock.resources.chartContainer';

// Janelas curtas (alta resolução, ideais para acompanhar em tempo real)
const liveRanges: { id: string; label: string; sub: string }[] = [
  { id: '15m', label: '15m', sub: 'Últimos 15 minutos' },
  { id: '1h', label: '1h', sub: 'Última hora' },
  { id: '6h', label: '6h', sub: 'Últimas 6 horas' },
];

// Atalhos de quantidade de dias
const dayPresets = [1, 3, 7, 15, 30];

const isValidRange = (r: string | null): r is string => !!r && /^\d+(m|h|d)$/.test(r);

const selectedRange = ref<string>(
  (() => {
    const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY_RANGE) : null;
    return isValidRange(saved) ? saved : '15m';
  })()
);
const customDays = ref<number>(
  selectedRange.value.endsWith('d') ? parseInt(selectedRange.value, 10) : 7
);

// Filtro de Contêiner Docker selecionado (vazio/null = Todo o Host + Docker Global)
const selectedContainer = ref<string>(
  (() => {
    const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY_CONTAINER) : null;
    return saved || '';
  })()
);

const availableContainers = ref<string[]>([]);
const loadingContainers = ref(false);

const selectedView = ref<ComponentView>('all');
const points = ref<(TelemetryHistoryPoint | (ContainerTelemetryPoint & { cpu_host?: number; disk_used_pct?: number }))[]>([]);
const loadingHistory = ref(false);
const isPaused = ref(false);
const lastSyncTime = ref<Date>(new Date());
const bucketSeconds = ref(5);
const windowSeconds = ref(900);
const oldestTimestamp = ref<number | null>(null);

// Quantidade de leituras já mescladas no último balde (média incremental ao vivo)
let lastBucketCount = 1;
let requestSeq = 0;

const isContainerFilterActive = computed(() => !!selectedContainer.value);

const componentViews = computed(() => {
  if (isContainerFilterActive.value) {
    return [
      { id: 'all' as ComponentView, label: 'Visão Geral Contêiner', icon: Layers },
      { id: 'cpu' as ComponentView, label: 'CPU Contêiner', icon: Cpu },
      { id: 'ram' as ComponentView, label: 'Memória RAM Contêiner', icon: Server },
      { id: 'network' as ComponentView, label: 'I/O de Rede Contêiner', icon: Network },
    ];
  }
  return [
    { id: 'all' as ComponentView, label: 'Visão Geral', icon: Layers },
    { id: 'cpu' as ComponentView, label: 'CPU (Host vs Docker)', icon: Cpu },
    { id: 'ram' as ComponentView, label: 'Memória RAM', icon: Server },
    { id: 'network' as ComponentView, label: 'I/O de Rede', icon: Network },
    { id: 'disk' as ComponentView, label: 'Armazenamento', icon: HardDrive },
  ];
});

// Se o usuário alternar para um contêiner e a view era 'disk', redefine para 'all'
watch(selectedContainer, (newContainer) => {
  try {
    localStorage.setItem(STORAGE_KEY_CONTAINER, newContainer);
  } catch {
    /* ignore */
  }
  if (newContainer && selectedView.value === 'disk') {
    selectedView.value = 'all';
  }
  loadHistory(selectedRange.value, newContainer);
});

// Atualiza a lista de contêineres conhecidos na janela (combinando a lista ao vivo do liveOverview e do backend)
const loadContainerList = async () => {
  loadingContainers.value = true;
  try {
    const res = await api.system.metricsContainers(selectedRange.value);
    const backendNames = res?.containers || [];
    const liveNames = (props.liveOverview?.docker_usage?.containers || []).map((c) => c.name);
    const combined = Array.from(new Set([...backendNames, ...liveNames])).filter(Boolean).sort();
    availableContainers.value = combined;
  } catch (err) {
    console.warn('Falha ao carregar lista de contêineres para métricas:', err);
  } finally {
    loadingContainers.value = false;
  }
};

watch(
  () => props.liveOverview?.docker_usage?.containers,
  (containers) => {
    if (!containers?.length) return;
    const liveNames = containers.map((c) => c.name);
    const combined = Array.from(new Set([...availableContainers.value, ...liveNames])).filter(Boolean).sort();
    if (combined.length !== availableContainers.value.length) {
      availableContainers.value = combined;
    }
  },
  { deep: true }
);

const selectedDays = computed(() =>
  selectedRange.value.endsWith('d') ? parseInt(selectedRange.value, 10) : null
);

const rangeDescription = computed(() => {
  const r = selectedRange.value;
  const n = parseInt(r, 10);
  if (r.endsWith('d')) return n === 1 ? 'Últimas 24 horas' : `Últimos ${n} dias`;
  if (r.endsWith('h')) return n === 1 ? 'Última hora' : `Últimas ${n} horas`;
  return `Últimos ${n} minutos`;
});

const resolutionLabel = computed(() => {
  const s = bucketSeconds.value;
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.round(s / 60)} min`;
  const h = s / 3600;
  return `${Number.isInteger(h) ? h : h.toFixed(1)} h`;
});

const selectRange = (range: string) => {
  selectedRange.value = range;
};

const selectDays = (days: number) => {
  const d = Math.min(MAX_DAYS, Math.max(1, Math.round(days || 1)));
  customDays.value = d;
  selectRange(`${d}d`);
};

const applyCustomDays = () => selectDays(customDays.value);

// Carrega histórico da API para a janela de tempo selecionada
const loadHistory = async (range: string, containerName = selectedContainer.value) => {
  const seq = ++requestSeq;
  loadingHistory.value = true;
  try {
    let res: any;
    if (containerName) {
      res = await api.system.containerMetricsHistory(containerName, range);
    } else {
      res = await api.system.metricsHistory(range);
    }
    if (seq !== requestSeq) return; // resposta de uma seleção anterior
    if (res && Array.isArray(res.points)) {
      points.value = res.points;
      bucketSeconds.value = res.bucket_seconds || 5;
      windowSeconds.value = res.window_seconds || 900;
      oldestTimestamp.value = res.oldest_timestamp ?? null;
      lastBucketCount = 1;
      lastSyncTime.value = new Date();
    }
  } catch (err) {
    console.warn('Falha ao carregar histórico de métricas:', err);
  } finally {
    if (seq === requestSeq) loadingHistory.value = false;
  }
};

watch(selectedRange, (newRange) => {
  try {
    localStorage.setItem(STORAGE_KEY_RANGE, newRange);
  } catch {
    /* armazenamento indisponível */
  }
  loadHistory(newRange, selectedContainer.value);
  loadContainerList();
});

const NUMERIC_HOST_FIELDS = [
  'cpu_host',
  'cpu_docker',
  'memory_host_pct',
  'memory_host_used_mb',
  'memory_docker_used_mb',
  'network_rx_mb',
  'network_tx_mb',
  'disk_used_pct',
  'containers_active',
] as const;

const NUMERIC_CONTAINER_FIELDS = [
  'cpu_percent',
  'memory_mb',
  'memory_host_pct',
  'network_rx_mb',
  'network_tx_mb',
] as const;

// Incorpora as leituras em tempo real (polling do parent) na série exibida
watch(
  () => props.liveOverview,
  (live) => {
    if (!live || isPaused.value || loadingHistory.value) return;

    const now = Date.now() / 1000;
    const bucket = Math.max(1, bucketSeconds.value);
    const bucketStart = Math.floor(now / bucket) * bucket;

    if (isContainerFilterActive.value) {
      // Filtrando por contêiner Docker específico
      const targetName = selectedContainer.value;
      const cLive = (live.docker_usage?.containers || []).find((c) => c.name === targetName);
      if (!cLive) return;

      const reading: ContainerTelemetryPoint = {
        timestamp: bucketStart,
        cpu_percent: cLive.cpu_percent || 0,
        cpu_percent_max: cLive.cpu_percent || 0,
        memory_mb: cLive.memory_usage_mb || 0,
        memory_host_pct: cLive.memory_host_percent || 0,
        network_rx_mb: cLive.network_rx_mb || 0,
        network_tx_mb: cLive.network_tx_mb || 0,
      };

      const current = [...points.value] as ContainerTelemetryPoint[];
      const last = current[current.length - 1];

      if (last && Math.abs(last.timestamp - bucketStart) < 0.5) {
        const n = lastBucketCount + 1;
        const merged = { ...last };
        for (const f of NUMERIC_CONTAINER_FIELDS) {
          merged[f] = ((last[f] || 0) * lastBucketCount + reading[f]) / n;
        }
        merged.cpu_percent_max = Math.max(last.cpu_percent_max ?? last.cpu_percent ?? 0, reading.cpu_percent);
        current[current.length - 1] = merged;
        lastBucketCount = n;
      } else {
        current.push(reading);
        lastBucketCount = 1;
      }

      const windowStart = now - windowSeconds.value;
      while (current.length > 1 && current[0]!.timestamp < windowStart) {
        current.shift();
      }
      points.value = current;
      lastSyncTime.value = new Date();
      return;
    }

    // Modo Host Completo
    const cpuHost = live.host.cpu_percent || 0;
    const reading: TelemetryHistoryPoint = {
      timestamp: bucketStart,
      cpu_host: cpuHost,
      cpu_host_max: cpuHost,
      cpu_docker: live.docker_usage.cpu_normalized_percent || 0,
      memory_host_pct: live.host.memory_percent || 0,
      memory_host_used_mb: live.host.memory_used_mb || 0,
      memory_docker_used_mb: live.docker_usage.memory_used_mb || 0,
      network_rx_mb: live.docker_usage.network_rx_mb || 0,
      network_tx_mb: live.docker_usage.network_tx_mb || 0,
      disk_used_pct: live.host.disks?.[0]?.percent || 0,
      containers_active: live.docker_usage.containers_running || 0,
    };

    const current = [...points.value] as TelemetryHistoryPoint[];
    const last = current[current.length - 1];

    if (last && Math.abs(last.timestamp - bucketStart) < 0.5) {
      // Mesmo balde: atualiza a média incremental e o pico
      const n = lastBucketCount + 1;
      const merged = { ...last };
      for (const f of NUMERIC_HOST_FIELDS) {
        merged[f] = (last[f] * lastBucketCount + reading[f]) / n;
      }
      merged.cpu_host_max = Math.max(last.cpu_host_max ?? last.cpu_host, cpuHost);
      current[current.length - 1] = merged;
      lastBucketCount = n;
    } else {
      current.push(reading);
      lastBucketCount = 1;
    }

    // Descarta pontos que saíram da janela selecionada
    const windowStart = now - windowSeconds.value;
    while (current.length > 1 && current[0]!.timestamp < windowStart) {
      current.shift();
    }

    points.value = current;
    lastSyncTime.value = new Date();
  }
);

onMounted(() => {
  loadHistory(selectedRange.value, selectedContainer.value);
  loadContainerList();
});

// Formatação do eixo X conforme a janela selecionada
const formatTimestamp = (ts: number): string => {
  const d = new Date(ts * 1000);
  const w = windowSeconds.value;
  if (w <= 3600) {
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  if (w <= 86400) {
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
  return `${d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })} ${d.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })}`;
};

const formatDateTime = (ts: number) =>
  new Date(ts * 1000).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

// Aviso quando ainda não há histórico cobrindo toda a janela pedida
const coverageNotice = computed(() => {
  if (!oldestTimestamp.value || !points.value.length) return null;
  const windowStart = Date.now() / 1000 - windowSeconds.value;
  const gap = oldestTimestamp.value - windowStart;
  if (gap < Math.max(bucketSeconds.value * 3, windowSeconds.value * 0.05)) return null;
  return `Histórico disponível desde ${formatDateTime(oldestTimestamp.value)}. O período completo será preenchido conforme a coleta contínua avança.`;
});

const lastSyncLabel = computed(() =>
  lastSyncTime.value.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
);

// Estatísticas Computadas para o componente selecionado
const activeStats = computed(() => {
  const pts = points.value;
  if (!pts.length) {
    return { current: 0, peak: 0, avg: 0, min: 0, unit: '%' };
  }

  let values: number[] = [];
  let peaks: number[] | null = null;
  let unit = '%';

  if (isContainerFilterActive.value) {
    const cPts = pts as ContainerTelemetryPoint[];
    if (selectedView.value === 'cpu' || selectedView.value === 'all') {
      values = cPts.map((p) => p.cpu_percent || 0);
      peaks = cPts.map((p) => p.cpu_percent_max ?? p.cpu_percent ?? 0);
    } else if (selectedView.value === 'ram') {
      values = cPts.map((p) => p.memory_mb || 0);
      unit = ' MB';
    } else if (selectedView.value === 'network') {
      values = cPts.map((p) => (p.network_rx_mb || 0) + (p.network_tx_mb || 0));
      unit = ' MB';
    }
  } else {
    const hPts = pts as TelemetryHistoryPoint[];
    if (selectedView.value === 'cpu' || selectedView.value === 'all') {
      values = hPts.map((p) => p.cpu_host);
      peaks = hPts.map((p) => p.cpu_host_max ?? p.cpu_host);
    } else if (selectedView.value === 'ram') {
      values = hPts.map((p) => p.memory_host_pct);
    } else if (selectedView.value === 'network') {
      values = hPts.map((p) => p.network_rx_mb + p.network_tx_mb);
      unit = ' MB';
    } else if (selectedView.value === 'disk') {
      values = hPts.map((p) => p.disk_used_pct);
    }
  }

  const current = values[values.length - 1] || 0;
  const peak = Math.max(...(peaks ?? values), 0);
  const min = Math.min(...values);
  const avg = values.reduce((a, b) => a + b, 0) / (values.length || 1);

  return {
    current: +current.toFixed(1),
    peak: +peak.toFixed(1),
    avg: +avg.toFixed(1),
    min: +(Number.isFinite(min) ? min : 0).toFixed(1),
    unit,
  };
});

const gradient = (rgb: string, top = 0.35) => (context: any) => {
  const { ctx, chartArea } = context.chart;
  if (!chartArea) return `rgba(${rgb}, ${top / 2})`;
  const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
  g.addColorStop(0, `rgba(${rgb}, ${top})`);
  g.addColorStop(1, `rgba(${rgb}, 0)`);
  return g;
};

// Configuração do Chart.js
const chartData = computed(() => {
  const pts = points.value;
  const labels = pts.map((p) => formatTimestamp(p.timestamp));
  const showDots = pts.length < 30 ? 2 : 0;
  const datasets: any[] = [];

  const base = { tension: 0.35, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 };

  if (isContainerFilterActive.value) {
    // VISUALIZAÇÃO FILTRADA POR CONTÊINER DOCKER
    const cPts = pts as ContainerTelemetryPoint[];
    const cName = selectedContainer.value;

    if (selectedView.value === 'all') {
      datasets.push(
        {
          ...base,
          label: `CPU ${cName} (%)`,
          data: cPts.map((p) => +(p.cpu_percent || 0).toFixed(2)),
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          fill: true,
        },
        {
          ...base,
          label: `Memória RAM (MB)`,
          data: cPts.map((p) => +(p.memory_mb || 0).toFixed(1)),
          borderColor: '#34d399',
          backgroundColor: 'transparent',
          yAxisID: 'y1',
        },
        {
          ...base,
          label: `RAM (% Host)`,
          data: cPts.map((p) => +(p.memory_host_pct || 0).toFixed(2)),
          borderColor: '#818cf8',
          backgroundColor: 'transparent',
          borderDash: [3, 3],
        }
      );
    } else if (selectedView.value === 'cpu') {
      datasets.push(
        {
          ...base,
          label: `CPU ${cName} (%)`,
          data: cPts.map((p) => +(p.cpu_percent || 0).toFixed(2)),
          borderColor: '#38bdf8',
          backgroundColor: gradient('56, 189, 248'),
          fill: true,
          borderWidth: 2.5,
          pointRadius: showDots,
          pointHoverRadius: 5,
        },
        {
          ...base,
          label: `Pico CPU (%)`,
          data: cPts.map((p) => +(p.cpu_percent_max ?? p.cpu_percent ?? 0).toFixed(2)),
          borderColor: 'rgba(248, 113, 113, 0.7)',
          backgroundColor: 'transparent',
          borderDash: [3, 3],
          borderWidth: 1.25,
        }
      );
    } else if (selectedView.value === 'ram') {
      datasets.push(
        {
          ...base,
          label: `Uso de RAM (MB)`,
          data: cPts.map((p) => +(p.memory_mb || 0).toFixed(1)),
          borderColor: '#10b981',
          backgroundColor: gradient('16, 185, 129'),
          fill: true,
          borderWidth: 2.5,
          pointRadius: showDots,
          pointHoverRadius: 5,
        },
        {
          ...base,
          label: `Share da RAM do Host (%)`,
          data: cPts.map((p) => +(p.memory_host_pct || 0).toFixed(2)),
          borderColor: '#a855f7',
          backgroundColor: 'transparent',
          borderDash: [4, 4],
          borderWidth: 1.5,
          yAxisID: 'y1',
        }
      );
    } else if (selectedView.value === 'network') {
      datasets.push(
        {
          ...base,
          label: 'Download / RX (MB)',
          data: cPts.map((p) => +(p.network_rx_mb || 0).toFixed(2)),
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.15)',
          fill: true,
          pointRadius: showDots,
          pointHoverRadius: 5,
        },
        {
          ...base,
          label: 'Upload / TX (MB)',
          data: cPts.map((p) => +(p.network_tx_mb || 0).toFixed(2)),
          borderColor: '#ec4899',
          backgroundColor: 'rgba(236, 72, 153, 0.12)',
          fill: true,
          pointRadius: showDots,
          pointHoverRadius: 5,
        }
      );
    }
  } else {
    // VISUALIZAÇÃO GLOBAL (HOST + DOCKER TOTAL)
    const hPts = pts as TelemetryHistoryPoint[];

    if (selectedView.value === 'all') {
      datasets.push(
        {
          ...base,
          label: 'CPU Host Real (%)',
          data: hPts.map((p) => +p.cpu_host.toFixed(1)),
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.08)',
          fill: true,
        },
        {
          ...base,
          label: 'CPU Docker (%)',
          data: hPts.map((p) => +p.cpu_docker.toFixed(1)),
          borderColor: '#818cf8',
          backgroundColor: 'transparent',
          borderDash: [4, 4],
        },
        {
          ...base,
          label: 'RAM Host (%)',
          data: hPts.map((p) => +p.memory_host_pct.toFixed(1)),
          borderColor: '#34d399',
          backgroundColor: 'rgba(52, 211, 153, 0.05)',
          fill: true,
        },
        {
          ...base,
          label: 'Disco Host (%)',
          data: hPts.map((p) => +p.disk_used_pct.toFixed(1)),
          borderColor: '#f59e0b',
          backgroundColor: 'transparent',
          borderDash: [2, 2],
          borderWidth: 1.5,
        }
      );
    } else if (selectedView.value === 'cpu') {
      datasets.push(
        {
          ...base,
          label: 'CPU Host Real (%)',
          data: hPts.map((p) => +p.cpu_host.toFixed(1)),
          borderColor: '#38bdf8',
          backgroundColor: gradient('56, 189, 248'),
          fill: true,
          borderWidth: 2.5,
          pointRadius: showDots,
          pointHoverRadius: 5,
        },
        {
          ...base,
          label: 'Pico CPU Host (%)',
          data: hPts.map((p) => +(p.cpu_host_max ?? p.cpu_host).toFixed(1)),
          borderColor: 'rgba(248, 113, 113, 0.7)',
          backgroundColor: 'transparent',
          borderDash: [3, 3],
          borderWidth: 1.25,
        },
        {
          ...base,
          label: 'CPU Consumida pelo Docker (%)',
          data: hPts.map((p) => +p.cpu_docker.toFixed(1)),
          borderColor: '#a855f7',
          backgroundColor: gradient('168, 85, 247', 0.25),
          fill: true,
          pointRadius: showDots,
          pointHoverRadius: 5,
        }
      );
    } else if (selectedView.value === 'ram') {
      datasets.push({
        ...base,
        label: 'RAM Host Real (%)',
        data: hPts.map((p) => +p.memory_host_pct.toFixed(1)),
        borderColor: '#10b981',
        backgroundColor: gradient('16, 185, 129'),
        fill: true,
        borderWidth: 2.5,
        pointRadius: showDots,
        pointHoverRadius: 5,
      });
    } else if (selectedView.value === 'network') {
      datasets.push(
        {
          ...base,
          label: 'Download / RX (MB)',
          data: hPts.map((p) => +p.network_rx_mb.toFixed(2)),
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.15)',
          fill: true,
          pointRadius: showDots,
          pointHoverRadius: 5,
        },
        {
          ...base,
          label: 'Upload / TX (MB)',
          data: hPts.map((p) => +p.network_tx_mb.toFixed(2)),
          borderColor: '#ec4899',
          backgroundColor: 'rgba(236, 72, 153, 0.12)',
          fill: true,
          pointRadius: showDots,
          pointHoverRadius: 5,
        }
      );
    } else if (selectedView.value === 'disk') {
      datasets.push({
        ...base,
        label: 'Ocupação de Disco Host (%)',
        data: hPts.map((p) => +p.disk_used_pct.toFixed(1)),
        borderColor: '#f59e0b',
        backgroundColor: gradient('245, 158, 11'),
        fill: true,
        tension: 0.3,
        borderWidth: 2.5,
        pointRadius: showDots,
        pointHoverRadius: 5,
      });
    }
  }

  return { labels, datasets };
});

const chartOptions = computed<ChartOptions<'line'>>(() => {
  const isPercent =
    isContainerFilterActive.value
      ? selectedView.value === 'cpu' || selectedView.value === 'all'
      : selectedView.value !== 'network';

  const needsSecondAxis =
    isContainerFilterActive.value && (selectedView.value === 'all' || selectedView.value === 'ram');

  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 200 },
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
        align: 'end',
        labels: {
          color: '#94a3b8',
          font: { size: 11, family: 'monospace' },
          boxWidth: 12,
          boxHeight: 12,
          usePointStyle: true,
          pointStyle: 'circle',
        },
      },
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 10,
        boxPadding: 4,
        usePointStyle: true,
        callbacks: {
          title: (items: any[]) => {
            const p = points.value[items[0]?.dataIndex ?? -1];
            return p ? formatDateTime(p.timestamp) + (bucketSeconds.value >= 60 ? ` (média ${resolutionLabel.value})` : '') : '';
          },
          label: (item: any) => {
            const dsLabel = item.dataset.label || '';
            const unit = dsLabel.includes('MB') ? ' MB' : dsLabel.includes('%') ? '%' : isPercent ? '%' : ' MB';
            return ` ${dsLabel}: ${item.formattedValue}${unit.startsWith(' ') ? unit : ' ' + unit}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(51, 65, 85, 0.35)',
        },
        ticks: {
          color: '#64748b',
          maxTicksLimit: 8,
          maxRotation: 0,
          autoSkip: true,
          font: { size: 10, family: 'monospace' },
        },
      },
      y: {
        min: 0,
        grid: {
          color: 'rgba(51, 65, 85, 0.35)',
        },
        ticks: {
          color: '#64748b',
          maxTicksLimit: 6,
          font: { size: 10, family: 'monospace' },
          callback: (value: any) =>
            isContainerFilterActive.value && selectedView.value === 'ram'
              ? `${value} MB`
              : isPercent
              ? `${value}%`
              : `${value} MB`,
        },
      },
      y1: {
        display: needsSecondAxis,
        position: 'right',
        min: 0,
        grid: {
          drawOnChartArea: false,
        },
        ticks: {
          color: '#818cf8',
          maxTicksLimit: 5,
          font: { size: 10, family: 'monospace' },
          callback: (value: any) =>
            selectedView.value === 'ram' ? `${value}%` : `${value} MB`,
        },
      },
    },
  };
});
</script>

<template>
  <div class="glass-panel p-5 space-y-4">
    <!-- Cabeçalho com Título, Filtro por Docker e Status em Tempo Real -->
    <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-4 pb-3 border-b border-dock-border">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-dock-accent/10 border border-dock-accent/30 flex items-center justify-center text-dock-accent shrink-0">
          <Activity class="w-4 h-4" :class="{ 'animate-pulse': !isPaused }" />
        </div>
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <h3 class="text-sm font-semibold text-dock-text">
              Histórico de Uso de Recursos
            </h3>
            <!-- Tag se estiver filtrando por contêiner -->
            <span
              v-if="isContainerFilterActive"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-dock-accent/10 text-dock-accent border border-dock-accent/30"
            >
              <Box class="w-3 h-3" />
              {{ selectedContainer }}
            </span>
            <!-- Indicador ao vivo -->
            <span
              class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium border"
              :class="
                !isPaused
                  ? 'bg-dock-success/10 text-dock-success border-dock-success/30'
                  : 'bg-dock-warning/10 text-dock-warning border-dock-warning/30'
              "
            >
              <span class="relative flex w-1.5 h-1.5">
                <span
                  v-if="!isPaused"
                  class="absolute inline-flex h-full w-full rounded-full bg-dock-success opacity-75 animate-ping"
                ></span>
                <span
                  class="relative inline-flex w-1.5 h-1.5 rounded-full"
                  :class="!isPaused ? 'bg-dock-success' : 'bg-dock-warning'"
                ></span>
              </span>
              {{ !isPaused ? 'Ao Vivo' : 'Pausado' }}
            </span>
          </div>
          <p class="text-xs text-dock-text-dim mt-0.5 font-mono">
            {{ isContainerFilterActive ? `Métricas do contêiner "${selectedContainer}"` : 'Servidor Host Completo & Docker' }}
            • {{ rangeDescription }} • resolução {{ resolutionLabel }} • atualizado às {{ lastSyncLabel }}
          </p>
        </div>
      </div>

      <!-- Controles Superiores: Filtro por Contêiner Docker + Seletor de Período -->
      <div class="flex flex-wrap items-center gap-2 self-start xl:self-auto">
        <!-- FILTRO POR DOCKER / CONTÊINER -->
        <div class="flex items-center gap-1.5 bg-dock-bg px-2.5 py-1 rounded-lg border border-dock-border">
          <Filter class="w-3.5 h-3.5 text-dock-text-dim" />
          <span class="text-[10px] font-mono uppercase tracking-wider text-dock-text-dim hidden sm:inline">
            Docker:
          </span>
          <select
            v-model="selectedContainer"
            class="bg-transparent text-xs font-mono text-dock-text focus:outline-none cursor-pointer pr-1"
            title="Filtrar métricas do gráfico por contêiner Docker"
          >
            <option value="" class="bg-dock-surface text-dock-text">
              Todos os Recursos (Host + Docker)
            </option>
            <optgroup label="Contêineres Docker">
              <option
                v-for="cName in availableContainers"
                :key="cName"
                :value="cName"
                class="bg-dock-surface text-dock-text"
              >
                {{ cName }}
              </option>
            </optgroup>
          </select>
        </div>

        <!-- Janelas Rápidas (Agora) -->
        <div class="flex items-center gap-1 bg-dock-bg p-1 rounded-lg border border-dock-border">
          <span class="text-[10px] font-mono uppercase tracking-wider text-dock-text-dim px-1.5 hidden sm:inline">
            Agora
          </span>
          <button
            v-for="r in liveRanges"
            :key="r.id"
            @click="selectRange(r.id)"
            class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-all cursor-pointer"
            :class="
              selectedRange === r.id
                ? 'bg-dock-accent text-dock-bg font-bold shadow-xs'
                : 'text-dock-text-muted hover:text-dock-text hover:bg-dock-surface'
            "
            :title="r.sub"
          >
            {{ r.label }}
          </button>
        </div>

        <!-- Janelas em Dias -->
        <div class="flex items-center gap-1 bg-dock-bg p-1 rounded-lg border border-dock-border">
          <span class="text-[10px] font-mono uppercase tracking-wider text-dock-text-dim px-1.5 flex items-center gap-1">
            <CalendarDays class="w-3 h-3" /> Dias
          </span>
          <button
            v-for="d in dayPresets"
            :key="d"
            @click="selectDays(d)"
            class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-all cursor-pointer"
            :class="
              selectedDays === d
                ? 'bg-dock-accent text-dock-bg font-bold shadow-xs'
                : 'text-dock-text-muted hover:text-dock-text hover:bg-dock-surface'
            "
            :title="d === 1 ? 'Últimas 24 horas' : `Últimos ${d} dias`"
          >
            {{ d }}d
          </button>
          <form class="flex items-center gap-1 pl-1 ml-0.5 border-l border-dock-border" @submit.prevent="applyCustomDays">
            <input
              v-model.number="customDays"
              type="number"
              min="1"
              :max="MAX_DAYS"
              step="1"
              class="w-14 px-1.5 py-0.5 rounded bg-dock-surface border text-xs font-mono text-dock-text tabular-nums focus:outline-none focus:border-dock-accent"
              :class="
                selectedDays !== null && !dayPresets.includes(selectedDays)
                  ? 'border-dock-accent'
                  : 'border-dock-border'
              "
              :title="`Quantidade de dias (1 a ${MAX_DAYS})`"
              aria-label="Quantidade de dias"
            />
            <button
              type="submit"
              class="px-2 py-1 rounded text-[11px] font-mono text-dock-text-muted hover:text-dock-text hover:bg-dock-surface transition-colors cursor-pointer"
            >
              Ver
            </button>
          </form>
        </div>
      </div>
    </div>

    <!-- Barra de Seleção de Componentes e Controles de Live Play/Pause -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <!-- Abas dos Componentes -->
      <div class="flex flex-wrap items-center gap-1">
        <button
          v-for="view in componentViews"
          :key="view.id"
          @click="selectedView = view.id"
          class="px-2.5 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer border"
          :class="
            selectedView === view.id
              ? 'bg-dock-surface border-dock-border-light text-dock-text'
              : 'bg-transparent border-transparent text-dock-text-dim hover:text-dock-text-muted hover:bg-dock-surface/50'
          "
        >
          <component :is="view.icon" class="w-3.5 h-3.5" />
          <span>{{ view.label }}</span>
        </button>
      </div>

      <!-- Botões de Controle de Fluxo -->
      <div class="flex items-center gap-2 self-end sm:self-auto">
        <button
          @click="isPaused = !isPaused"
          class="px-2.5 py-1 rounded text-xs font-mono border transition-colors flex items-center gap-1.5 cursor-pointer"
          :class="
            isPaused
              ? 'bg-dock-warning/10 border-dock-warning/30 text-dock-warning'
              : 'bg-dock-bg border-dock-border text-dock-text-dim hover:text-dock-text'
          "
          :title="isPaused ? 'Retomar atualização contínua' : 'Pausar atualização contínua'"
        >
          <Play v-if="isPaused" class="w-3 h-3" />
          <Pause v-else class="w-3 h-3" />
          <span>{{ isPaused ? 'Retomar' : 'Congelar' }}</span>
        </button>

        <button
          @click="loadHistory(selectedRange, selectedContainer)"
          :disabled="loadingHistory"
          class="p-1.5 rounded text-xs border border-dock-border bg-dock-bg hover:bg-dock-surface text-dock-text-dim hover:text-dock-text transition-colors cursor-pointer"
          title="Recarregar histórico"
        >
          <RotateCcw class="w-3.5 h-3.5" :class="{ 'animate-spin': loadingHistory }" />
        </button>
      </div>
    </div>

    <!-- Aviso de cobertura parcial do período -->
    <div
      v-if="coverageNotice"
      class="flex items-start gap-2 px-3 py-2 rounded border border-dock-border bg-dock-bg text-[11px] font-mono text-dock-text-dim"
    >
      <Info class="w-3.5 h-3.5 shrink-0 mt-px" />
      <span>{{ coverageNotice }}</span>
    </div>

    <!-- Área Principal do Gráfico -->
    <div class="relative w-full h-72 sm:h-80 bg-dock-bg/50 rounded-lg p-3 border border-dock-border">
      <div
        v-if="loadingHistory"
        class="absolute inset-0 flex items-center justify-center bg-dock-bg/70 z-10 rounded-lg"
      >
        <span class="text-xs font-mono text-dock-text-dim animate-pulse">
          Carregando série temporal...
        </span>
      </div>
      <div
        v-else-if="!points.length"
        class="absolute inset-0 flex flex-col items-center justify-center gap-2 z-10 rounded-lg"
      >
        <Box v-if="isContainerFilterActive" class="w-8 h-8 text-dock-text-dim/50" />
        <span class="text-xs font-mono text-dock-text-dim text-center px-4">
          {{
            isContainerFilterActive
              ? `Aguardando primeiras métricas coletadas para o contêiner "${selectedContainer}"...`
              : 'Aguardando as primeiras amostras de telemetria...'
          }}
        </span>
      </div>

      <Line :data="chartData" :options="chartOptions" />
    </div>

    <!-- Ticker de Métricas / Estatísticas no Período -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1 text-xs font-mono">
      <div class="bg-dock-bg border border-dock-border rounded p-2.5">
        <div class="text-[10px] uppercase text-dock-text-dim">Leitura Atual</div>
        <div class="text-base font-bold text-dock-text mt-0.5 tabular-nums">
          {{ activeStats.current }}{{ activeStats.unit }}
        </div>
      </div>
      <div class="bg-dock-bg border border-dock-border rounded p-2.5">
        <div class="text-[10px] uppercase text-dock-text-dim">Pico no Período</div>
        <div class="text-base font-bold text-dock-error mt-0.5 tabular-nums">
          {{ activeStats.peak }}{{ activeStats.unit }}
        </div>
      </div>
      <div class="bg-dock-bg border border-dock-border rounded p-2.5">
        <div class="text-[10px] uppercase text-dock-text-dim">Média do Período</div>
        <div class="text-base font-bold text-dock-accent mt-0.5 tabular-nums">
          {{ activeStats.avg }}{{ activeStats.unit }}
        </div>
      </div>
      <div class="bg-dock-bg border border-dock-border rounded p-2.5">
        <div class="text-[10px] uppercase text-dock-text-dim">Mínimo Observado</div>
        <div class="text-base font-bold text-dock-success mt-0.5 tabular-nums">
          {{ activeStats.min }}{{ activeStats.unit }}
        </div>
      </div>
    </div>
  </div>
</template>
