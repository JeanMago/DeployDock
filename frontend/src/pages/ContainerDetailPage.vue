<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  ArrowLeft,
  Info,
  Activity,
  Terminal,
  FileText,
  Play,
  Trash2,
  FolderOpen,
  Folder,
  FileCode,
  CornerLeftUp,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { ContainerDetail } from '@/services/types';
import StatusBadge from '@/components/common/StatusBadge.vue';
import ContainerActions from '@/components/containers/ContainerActions.vue';
import MetricsChart from '@/components/containers/MetricsChart.vue';
import LogViewer from '@/components/containers/LogViewer.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import { useContainerMetrics } from '@/composables/useContainerMetrics';

const route = useRoute();
const router = useRouter();
const container = ref<ContainerDetail | null>(null);
const activeTab = ref<'overview' | 'logs' | 'metrics' | 'exec' | 'files'>(
  ((route.query.tab as string) as any) || 'logs'
);
const loading = ref(true);

const { metrics } = useContainerMetrics(route.params.id as string);

const cpuData = computed(() => metrics.value.map((m) => m.cpu_percent));
const memData = computed(() => metrics.value.map((m) => m.memory_percent));
const labels = computed(() =>
  metrics.value.map((m) => (m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : ''))
);

// Estado do Console de Execução de Comandos (Container Exec)
const execCommand = ref('');
const execWorkdir = ref('');
const execRunning = ref(false);
const execHistory = ref<
  { id: number; command: string; output: string; exitCode: number; time: string }[]
>([]);
let execSeq = 1;

const quickCommands = [
  { label: 'Listar Arquivos (ls -la)', cmd: 'ls -la' },
  { label: 'Processos Ativos (ps aux)', cmd: 'ps aux' },
  { label: 'Uso de Disco (df -h)', cmd: 'df -h' },
  { label: 'Sistema Operacional', cmd: 'cat /etc/os-release' },
  { label: ' Portas Abertas', cmd: 'netstat -tlpn 2>/dev/null || ss -tlpn' },
  { label: 'Variáveis (env)', cmd: 'env | sort' },
];

const runExecCommand = async (customCmd?: string) => {
  const cmd = (customCmd ?? execCommand.value).trim();
  if (!cmd || !container.value) return;
  execRunning.value = true;
  try {
    const res = await api.containers.exec(
      container.value.id,
      cmd,
      execWorkdir.value.trim() || undefined
    );
    execHistory.value.unshift({
      id: execSeq++,
      command: cmd,
      output: res.output || '(sem saída)',
      exitCode: res.exit_code,
      time: new Date().toLocaleTimeString('pt-BR', { hour12: false }),
    });
    if (!customCmd) execCommand.value = '';
  } catch (err: any) {
    execHistory.value.unshift({
      id: execSeq++,
      command: cmd,
      output: `Erro: ${err.message || err}`,
      exitCode: 1,
      time: new Date().toLocaleTimeString('pt-BR', { hour12: false }),
    });
  } finally {
    execRunning.value = false;
  }
};

const networkMode = computed(() => {
  if (!container.value) return 'bridge';
  if (container.value.networks && Object.keys(container.value.networks).length) {
    return Object.keys(container.value.networks).join(', ');
  }
  return 'bridge';
});

const formattedPorts = computed(() => {
  if (!container.value?.ports || typeof container.value.ports !== 'object') return [];
  const result: string[] = [];
  for (const [containerPort, bindings] of Object.entries(container.value.ports)) {
    if (Array.isArray(bindings) && bindings.length > 0) {
      for (const b of bindings) {
        if (b && typeof b === 'object' && 'HostPort' in b) {
          result.push(`${(b as Record<string, unknown>).HostPort}:${containerPort}`);
        } else {
          result.push(containerPort);
        }
      }
    } else {
      result.push(containerPort);
    }
  }
  return result;
});

const load = async () => {
  try {
    container.value = await api.containers.get(route.params.id as string);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

// Estado do Explorador de Arquivos do Contêiner
const currentDir = ref('/');
const dirItems = ref<
  {
    name: string;
    path: string;
    is_dir: boolean;
    is_link: boolean;
    permissions: string;
    owner: string;
    size: string;
    modified: string;
  }[]
>([]);
const loadingFiles = ref(false);
const viewingFile = ref<{ path: string; content: string } | null>(null);

const loadDirectory = async (targetPath: string = '/') => {
  if (!container.value || container.value.state !== 'running') return;
  loadingFiles.value = true;
  viewingFile.value = null;
  try {
    const res = await api.containers.listFiles(container.value.id, targetPath);
    currentDir.value = res.path;
    dirItems.value = res.items || [];
  } catch (e) {
    console.error(e);
  } finally {
    loadingFiles.value = false;
  }
};

const goUpDir = () => {
  if (currentDir.value === '/') return;
  const parts = currentDir.value.split('/').filter(Boolean);
  parts.pop();
  loadDirectory('/' + parts.join('/'));
};

const openFileOrDir = async (item: (typeof dirItems.value)[0]) => {
  if (item.is_dir) {
    await loadDirectory(item.path);
  } else if (container.value) {
    loadingFiles.value = true;
    try {
      const res = await api.containers.readFile(container.value.id, item.path);
      viewingFile.value = { path: res.path, content: res.content };
    } catch (e: any) {
      alert(e?.message || 'Erro ao ler arquivo');
    } finally {
      loadingFiles.value = false;
    }
  }
};

watch(activeTab, (tab) => {
  if (tab === 'files' && dirItems.value.length === 0) {
    loadDirectory('/');
  }
});

watch(
  () => route.query.tab,
  (val) => {
    if (val && ['overview', 'logs', 'metrics', 'exec', 'files'].includes(String(val))) {
      activeTab.value = String(val) as any;
    }
  }
);

onMounted(load);
</script>

<template>
  <div v-if="loading" class="flex justify-center py-20"><LoadingSpinner /></div>
  <div v-else-if="container" class="space-y-5">
    <!-- Cabeçalho Responsivo -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-dock-border">
      <div class="flex items-start sm:items-center gap-3 min-w-0">
        <button
          @click="router.back()"
          class="p-2 rounded bg-dock-surface border border-dock-border hover:border-dock-border-light text-dock-text-muted hover:text-dock-text transition-colors shrink-0 cursor-pointer"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="text-lg font-semibold text-dock-text truncate">
              {{ container.name }}
            </h1>
            <StatusBadge :status="container.state || container.status" size="sm" />
          </div>
          <div class="text-xs text-dock-text-dim font-mono mt-0.5 truncate">
            {{ container.image }} • id: {{ container.id.substring(0, 12) }}
          </div>
        </div>
      </div>
      <div class="self-start sm:self-auto">
        <ContainerActions
          :containerId="container.id"
          :status="container.state || container.status"
          @refresh="load"
        />
      </div>
    </div>

    <!-- Abas de Navegação Responsivas -->
    <div class="flex overflow-x-auto gap-1.5 p-1 glass-panel w-full sm:w-fit">
      <button
        @click="activeTab = 'logs'"
        class="px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'logs'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <FileText class="w-3.5 h-3.5" /> Logs da Aplicação
      </button>
      <button
        @click="activeTab = 'exec'"
        class="px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'exec'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <Terminal class="w-3.5 h-3.5" /> Terminal Exec (sh)
      </button>
      <button
        @click="activeTab = 'files'"
        class="px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'files'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <FolderOpen class="w-3.5 h-3.5" /> Arquivos do Contêiner
      </button>
      <button
        @click="activeTab = 'metrics'"
        class="px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'metrics'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <Activity class="w-3.5 h-3.5" /> Métricas em Tempo Real
      </button>
      <button
        @click="activeTab = 'overview'"
        class="px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
        :class="
          activeTab === 'overview'
            ? 'bg-dock-surface text-dock-text border border-dock-border-light'
            : 'text-dock-text-muted hover:text-dock-text border border-transparent'
        "
      >
        <Info class="w-3.5 h-3.5" /> Inspeção & Ambiente
      </button>
    </div>

    <!-- ABA 1: LOGS DA APLICAÇÃO -->
    <div v-if="activeTab === 'logs'">
      <LogViewer :containerId="container.id" />
    </div>

    <!-- ABA ARQUIVOS DO CONTÊINER -->
    <div v-else-if="activeTab === 'files'" class="glass-panel p-4 space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-dock-border pb-3">
        <div class="flex items-center gap-2 font-mono text-xs">
          <button
            @click="goUpDir"
            :disabled="currentDir === '/'"
            class="px-2 py-1 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-dock-text-muted hover:text-dock-text disabled:opacity-40 flex items-center gap-1 cursor-pointer"
          >
            <CornerLeftUp class="w-3.5 h-3.5" /> Subir
          </button>
          <span class="px-2.5 py-1 rounded bg-dock-bg border border-dock-border text-dock-accent">
            {{ currentDir }}
          </span>
        </div>

        <div class="flex flex-wrap gap-1.5 font-mono text-[11px]">
          <button
            v-for="quickPath in ['/', '/app', '/etc/nginx', '/usr/share/nginx/html', '/var/log']"
            :key="quickPath"
            @click="loadDirectory(quickPath)"
            class="px-2 py-1 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-dock-text-muted hover:text-dock-text cursor-pointer"
          >
            {{ quickPath }}
          </button>
        </div>
      </div>

      <!-- Visualizador de Arquivo Selecionado -->
      <div v-if="viewingFile" class="space-y-2">
        <div class="flex items-center justify-between bg-dock-surface px-3 py-2 rounded border border-dock-border font-mono text-xs">
          <span class="text-dock-text">{{ viewingFile.path }}</span>
          <button
            @click="viewingFile = null"
            class="px-2 py-0.5 rounded bg-dock-bg border border-dock-border text-dock-text-muted hover:text-dock-text cursor-pointer"
          >
            Voltar à pasta
          </button>
        </div>
        <pre class="p-3 rounded bg-dock-bg border border-dock-border font-mono text-xs text-dock-text max-h-[420px] overflow-auto whitespace-pre-wrap">{{ viewingFile.content || '(arquivo vazio)' }}</pre>
      </div>

      <!-- Tabela de Arquivos e Pastas -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-xs font-mono border-collapse">
          <thead>
            <tr class="border-b border-dock-border text-dock-text-dim text-[11px]">
              <th class="py-2 px-2.5">Nome</th>
              <th class="py-2 px-2.5">Permissões</th>
              <th class="py-2 px-2.5">Dono</th>
              <th class="py-2 px-2.5">Tamanho</th>
              <th class="py-2 px-2.5 text-right">Modificado</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-dock-border">
            <tr v-if="loadingFiles">
              <td colspan="5" class="py-8 text-center text-dock-text-dim">Carregando diretório...</td>
            </tr>
            <tr v-else-if="dirItems.length === 0">
              <td colspan="5" class="py-8 text-center text-dock-text-dim">Diretório vazio ou inacessível.</td>
            </tr>
            <tr
              v-for="item in dirItems"
              :key="item.path"
              @click="openFileOrDir(item)"
              class="hover:bg-dock-surface/60 cursor-pointer transition-colors"
            >
              <td class="py-2 px-2.5 flex items-center gap-2 text-dock-text">
                <Folder v-if="item.is_dir" class="w-3.5 h-3.5 text-dock-accent shrink-0" />
                <FileCode v-else class="w-3.5 h-3.5 text-dock-text-dim shrink-0" />
                <span :class="item.is_dir ? 'font-semibold text-dock-accent' : ''">{{ item.name }}</span>
              </td>
              <td class="py-2 px-2.5 text-dock-text-dim">{{ item.permissions }}</td>
              <td class="py-2 px-2.5 text-dock-text-muted">{{ item.owner }}</td>
              <td class="py-2 px-2.5 text-dock-text-muted">{{ item.size }} B</td>
              <td class="py-2 px-2.5 text-right text-dock-text-dim">{{ item.modified }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ABA 2: TERMINAL EXEC (EXECUÇÃO DE COMANDOS NO CONTÊINER) -->
    <div v-else-if="activeTab === 'exec'" class="space-y-4">
      <div class="glass-panel p-4 space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 class="text-sm font-semibold text-dock-text">Executar Comando no Contêiner (`/bin/sh -c`)</h3>
            <p class="text-xs text-dock-text-dim">
              Rode comandos de diagnóstico, inspecione arquivos ou verifique configurações diretamente dentro do contêiner.
            </p>
          </div>
          <span
            v-if="container.state !== 'running'"
            class="text-xs font-mono text-dock-warning bg-dock-warning/10 border border-dock-warning/30 px-2.5 py-1 rounded"
          >
            Inicie o contêiner para executar comandos
          </span>
        </div>

        <!-- Atalhos rápidos -->
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="q in quickCommands"
            :key="q.cmd"
            @click="runExecCommand(q.cmd)"
            :disabled="execRunning || container.state !== 'running'"
            class="px-2.5 py-1 rounded text-[11px] font-mono bg-dock-surface hover:bg-dock-bg border border-dock-border hover:border-dock-border-light text-dock-text-muted hover:text-dock-text disabled:opacity-40 transition-colors cursor-pointer"
          >
            $ {{ q.label }}
          </button>
        </div>

        <!-- Input de Comando -->
        <form @submit.prevent="runExecCommand()" class="flex flex-col sm:flex-row gap-2">
          <div class="flex items-center flex-1 bg-dock-bg border border-dock-border focus-within:border-dock-accent rounded px-3 py-1.5 font-mono text-xs">
            <span class="text-dock-accent mr-2 select-none">#</span>
            <input
              v-model="execCommand"
              type="text"
              placeholder="Digite um comando (ex: ls -la /usr/share/nginx/html, nginx -t, ps aux)..."
              :disabled="execRunning || container.state !== 'running'"
              class="w-full bg-transparent text-dock-text placeholder-dock-text-dim outline-none"
            />
          </div>
          <input
            v-model="execWorkdir"
            type="text"
            placeholder=" Diretório (opcional, ex: /app)"
            class="sm:w-48 bg-dock-bg border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-xs text-dock-text placeholder-dock-text-dim outline-none"
          />
          <button
            type="submit"
            :disabled="execRunning || !execCommand.trim() || container.state !== 'running'"
            class="px-4 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white text-xs font-medium transition-colors flex items-center justify-center gap-1.5 disabled:opacity-40 cursor-pointer shrink-0"
          >
            <Play class="w-3.5 h-3.5" />
            {{ execRunning ? 'Executando...' : 'Executar' }}
          </button>
        </form>
      </div>

      <!-- Histórico de Saídas do Terminal Exec -->
      <div class="glass-panel overflow-hidden">
        <div class="px-4 py-2.5 bg-dock-surface border-b border-dock-border flex items-center justify-between">
          <span class="text-xs font-mono text-dock-text-muted">Saída dos Comandos ({{ execHistory.length }})</span>
          <button
            v-if="execHistory.length"
            @click="execHistory = []"
            class="text-xs font-mono text-dock-text-dim hover:text-dock-error flex items-center gap-1 cursor-pointer"
          >
            <Trash2 class="w-3 h-3" /> Limpar histórico
          </button>
        </div>
        <div v-if="!execHistory.length" class="p-8 text-center text-xs font-mono text-dock-text-dim">
          Nenhum comando executado nesta sessão. Clique em um atalho acima ou digite um comando.
        </div>
        <div v-else class="divide-y divide-dock-border max-h-[460px] overflow-y-auto font-mono text-xs">
          <div v-for="item in execHistory" :key="item.id" class="p-3 bg-dock-bg space-y-2">
            <div class="flex items-center justify-between text-[11px]">
              <div class="flex items-center gap-2">
                <span class="text-dock-accent font-semibold">$ {{ item.command }}</span>
                <span class="text-dock-text-dim">{{ item.time }}</span>
              </div>
              <span
                class="px-1.5 py-0.5 rounded border text-[10px]"
                :class="
                  item.exitCode === 0
                    ? 'bg-dock-success/10 text-dock-success border-dock-success/30'
                    : 'bg-dock-error/10 text-dock-error border-dock-error/30'
                "
              >
                exit {{ item.exitCode }}
              </span>
            </div>
            <pre class="p-2.5 rounded bg-dock-surface border border-dock-border text-dock-text overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">{{ item.output }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 3: MÉTRICAS EM TEMPO REAL -->
    <div v-else-if="activeTab === 'metrics'" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <MetricsChart :data="cpuData" :labels="labels" label="Uso de CPU (%)" color="#3b82f6" :max="100" />
      <MetricsChart :data="memData" :labels="labels" label="Uso de Memória (%)" color="#10b981" :max="100" />
    </div>

    <!-- ABA 4: INSPEÇÃO & AMBIENTE -->
    <div v-else-if="activeTab === 'overview'" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="glass-panel p-4">
        <h3 class="text-xs font-semibold uppercase tracking-wider text-dock-text-muted mb-3 border-b border-dock-border pb-2">
          Variáveis de Ambiente do Contêiner ({{ container.env?.length || 0 }})
        </h3>
        <div class="space-y-1.5 max-h-72 overflow-y-auto font-mono text-xs">
          <div v-if="!container.env || !container.env.length" class="text-xs text-dock-text-dim">
            Nenhuma variável configurada.
          </div>
          <div
            v-for="env in container.env"
            :key="env"
            class="bg-dock-surface px-2.5 py-1.5 rounded border border-dock-border break-all text-dock-text-muted"
          >
            <span class="text-dock-accent">{{ env.split('=')[0] }}</span>=<span class="text-dock-text">{{ env.split('=').slice(1).join('=') }}</span>
          </div>
        </div>
      </div>

      <div class="glass-panel p-4 space-y-4">
        <h3 class="text-xs font-semibold uppercase tracking-wider text-dock-text-muted border-b border-dock-border pb-2">
          Rede, Portas & Volumes Montados
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <div class="text-[11px] font-mono text-dock-text-dim mb-1">Rede Conectada</div>
            <div class="font-mono text-xs bg-dock-surface px-2.5 py-1.5 rounded border border-dock-border text-dock-text">
              {{ networkMode }}
            </div>
          </div>
          <div>
            <div class="text-[11px] font-mono text-dock-text-dim mb-1">Política de Restart</div>
            <div class="font-mono text-xs bg-dock-surface px-2.5 py-1.5 rounded border border-dock-border text-dock-text">
              {{ (container.restart_policy as any)?.Name || 'no' }}
            </div>
          </div>
        </div>

        <div>
          <div class="text-[11px] font-mono text-dock-text-dim mb-1">Mapeamento de Portas</div>
          <div v-if="!formattedPorts.length" class="text-xs text-dock-text-muted">Nenhuma porta exposta</div>
          <div v-else class="flex flex-wrap gap-1.5 font-mono text-xs">
            <span
              v-for="p in formattedPorts"
              :key="p"
              class="bg-dock-surface px-2 py-1 rounded border border-dock-border text-dock-text"
            >
              {{ p }}
            </span>
          </div>
        </div>

        <div>
          <div class="text-[11px] font-mono text-dock-text-dim mb-1">Mounts / Volumes</div>
          <div v-if="!container.mounts || !container.mounts.length" class="text-xs text-dock-text-muted">
            Nenhum volume externo montado
          </div>
          <div v-else class="space-y-1.5 font-mono text-xs">
            <div
              v-for="(m, i) in container.mounts"
              :key="i"
              class="bg-dock-surface px-2.5 py-1.5 rounded border border-dock-border text-dock-text-muted break-all"
            >
              <span class="text-dock-text">{{ (m as any).Source || m.source }}</span> →
              <span class="text-dock-accent">{{ (m as any).Destination || m.destination }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
