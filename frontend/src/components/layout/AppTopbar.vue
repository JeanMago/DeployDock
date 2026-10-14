<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { Bell, Menu } from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemInfo } from '@/services/types';

defineEmits<{ (e: 'toggle-sidebar'): void }>();
const route = useRoute();

const sysInfo = ref<SystemInfo | null>(null);

const titlesMap: Record<string, string> = {
  'Dashboard': 'Painel Geral',
  'Containers': 'Contêineres Docker',
  'ContainerDetail': 'Detalhes do Contêiner',
  'Projects': 'Projetos GitOps',
  'Deployments': 'Histórico de Deploys',
  'Settings': 'Configurações do Sistema',
  'Tutorial': 'Central de Ajuda & Guia'
};

const pageTitle = computed(() => {
  const name = route.name?.toString() || '';
  return titlesMap[name] || name || 'Painel Geral';
});

const loadMetrics = async () => {
  try {
    sysInfo.value = await api.system.info();
  } catch (e) {
    // Silently ignore if offline
  }
};

let intervalId: any = null;

onMounted(() => {
  loadMetrics();
  intervalId = setInterval(loadMetrics, 10000);
});

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId);
});
</script>

<template>
  <header class="h-16 border-b border-dock-border/50 bg-dock-bg/80 backdrop-blur flex items-center justify-between px-6 sticky top-0 z-10">
    <div class="flex items-center gap-4">
      <button @click="$emit('toggle-sidebar')" class="lg:hidden p-2 -ml-2 text-dock-text-muted hover:text-dock-text rounded-md">
        <Menu class="w-5 h-5" />
      </button>
      <h1 class="text-xl font-semibold tracking-tight text-dock-text">{{ pageTitle }}</h1>
    </div>

    <div class="flex items-center gap-4">
      <div class="hidden md:flex items-center gap-3 px-3 py-1.5 rounded-full bg-dock-surface border border-dock-border text-sm">
        <div class="flex items-center gap-1.5">
          <span 
            class="w-2 h-2 rounded-full"
            :class="sysInfo && (sysInfo.containers_running || 0) > 0 ? 'bg-dock-success animate-pulse' : 'bg-dock-text-dim'"
          ></span>
          <span class="text-dock-text-muted">
            {{ sysInfo?.containers_running || 0 }} em execução
          </span>
        </div>
        <div class="w-px h-4 bg-dock-border"></div>
        <div class="text-dock-text-muted">CPUs: <span class="text-dock-text font-mono">{{ sysInfo?.cpus || 0 }}</span></div>
        <div class="w-px h-4 bg-dock-border"></div>
        <div class="text-dock-text-muted">Memória: <span class="text-dock-text font-mono">{{ sysInfo?.memory_total_mb ? (sysInfo.memory_total_mb / 1024).toFixed(1) + ' GB' : '--' }}</span></div>
      </div>

      <button class="p-2 text-dock-text-muted hover:text-dock-accent hover:bg-dock-accent/10 rounded-full transition-colors relative" title="Notificações">
        <Bell class="w-5 h-5" />
        <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-dock-accent rounded-full border-2 border-dock-bg"></span>
      </button>
    </div>
  </header>
</template>
