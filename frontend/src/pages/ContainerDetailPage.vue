<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeft, Info, Activity, Terminal } from 'lucide-vue-next';
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
const activeTab = ref('overview');
const loading = ref(true);

const { metrics } = useContainerMetrics(route.params.id as string);

const cpuData = computed(() => metrics.value.map(m => m.cpu_percent));
const memData = computed(() => metrics.value.map(m => m.memory_percent));
const labels = computed(() => metrics.value.map(m => new Date(m.timestamp).toLocaleTimeString()));

const load = async () => {
  try {
    container.value = await api.containers.get(route.params.id as string);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

onMounted(load);
</script>

<template>
  <div v-if="loading" class="flex justify-center py-20"><LoadingSpinner /></div>
  <div v-else-if="container" class="space-y-6">
    <div class="flex items-center gap-4 mb-2">
      <button @click="router.back()" class="p-2 rounded-lg glass-panel hover:bg-dock-surface text-dock-text-muted transition-colors"><ArrowLeft class="w-5 h-5"/></button>
      <div class="flex-1">
        <h1 class="text-2xl font-bold text-dock-text flex items-center gap-3">
          {{ container.name }}
          <StatusBadge :status="container.state" size="lg" pulse />
        </h1>
        <div class="text-sm text-dock-text-muted font-mono mt-1">{{ container.image }} • {{ container.id.substring(0, 12) }}</div>
      </div>
      <ContainerActions :containerId="container.id" :status="container.state" @refresh="load" />
    </div>

    <div class="flex gap-2 p-1 glass-panel rounded-lg w-fit">
      <button @click="activeTab = 'overview'" class="px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2" :class="activeTab === 'overview' ? 'bg-dock-surface text-dock-text shadow-sm' : 'text-dock-text-muted hover:text-dock-text'"><Info class="w-4 h-4"/> Overview</button>
      <button @click="activeTab = 'metrics'" class="px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2" :class="activeTab === 'metrics' ? 'bg-dock-surface text-dock-text shadow-sm' : 'text-dock-text-muted hover:text-dock-text'"><Activity class="w-4 h-4"/> Metrics</button>
      <button @click="activeTab = 'logs'" class="px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2" :class="activeTab === 'logs' ? 'bg-dock-surface text-dock-text shadow-sm' : 'text-dock-text-muted hover:text-dock-text'"><Terminal class="w-4 h-4"/> Logs</button>
    </div>

    <div v-if="activeTab === 'overview'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="glass-panel p-6">
        <h3 class="font-semibold mb-4 border-b border-dock-border pb-2">Environment Variables</h3>
        <div class="space-y-2 max-h-64 overflow-y-auto font-mono text-sm">
          <div v-for="env in container.env" :key="env" class="bg-dock-surface px-3 py-1.5 rounded border border-dock-border truncate text-dock-text-muted" :title="env">
            <span class="text-dock-accent">{{ env.split('=')[0] }}</span>=<span class="text-dock-text-dim">{{ env.split('=').slice(1).join('=') }}</span>
          </div>
        </div>
      </div>
      <div class="glass-panel p-6">
        <h3 class="font-semibold mb-4 border-b border-dock-border pb-2">Ports & Network</h3>
        <div class="space-y-4">
          <div>
            <div class="text-xs text-dock-text-dim mb-1">Network Mode</div>
            <div class="font-mono text-sm bg-dock-surface px-3 py-1.5 rounded inline-block border border-dock-border">{{ container.networkMode }}</div>
          </div>
          <div>
            <div class="text-xs text-dock-text-dim mb-1">Port Bindings</div>
            <div v-if="!container.ports.length" class="text-sm text-dock-text-muted">No ports exposed</div>
            <div class="space-y-2 font-mono text-sm">
              <div v-for="p in container.ports" :key="p.publicPort" class="flex items-center gap-2">
                <span class="bg-dock-surface px-2 py-1 rounded border border-dock-border">{{ p.ip || '0.0.0.0' }}:{{ p.publicPort }}</span>
                <ArrowLeft class="w-4 h-4 text-dock-text-dim" />
                <span class="bg-dock-surface px-2 py-1 rounded border border-dock-border">{{ p.privatePort }}/{{ p.type }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else-if="activeTab === 'metrics'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <MetricsChart :data="cpuData" :labels="labels" label="CPU Usage (%)" color="#0ea5e9" :max="100" />
      <MetricsChart :data="memData" :labels="labels" label="Memory Usage (%)" color="#22c55e" :max="100" />
    </div>
    
    <div v-else-if="activeTab === 'logs'">
      <LogViewer :containerId="container.id" />
    </div>
  </div>
</template>
