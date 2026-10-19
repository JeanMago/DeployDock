<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { Menu, LogOut, HardDrive, ShieldCheck, Search } from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemInfo } from '@/services/types';
import { useAuth } from '@/composables/useAuth';

const { currentUser, logout, canAccessDocker } = useAuth();

defineEmits<{
  (e: 'toggle-sidebar'): void;
  (e: 'open-palette'): void;
}>();
const route = useRoute();

const sysInfo = ref<SystemInfo | null>(null);

const titlesMap: Record<string, string> = {
  Dashboard: 'Visão Geral',
  Containers: 'Contêineres Docker',
  ContainerDetail: 'Inspeção de Contêiner',
  Projects: 'Projetos GitOps & 1-Click',
  Deployments: 'Histórico de Deploys',
  Resources: 'Recursos & Armazenamento',
  Security: 'Segurança, WAF & Firewall',
  Settings: 'Configurações do Sistema',
  Tutorial: 'Documentação & Guia',
};

const pageTitle = computed(() => {
  const name = route.name?.toString() || '';
  return titlesMap[name] || name || 'Visão Geral';
});

const loadMetrics = async () => {
  if (!canAccessDocker.value) return;
  try {
    sysInfo.value = await api.system.info();
  } catch {
    // Ignorar caso offline
  }
};

let intervalId: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  loadMetrics();
  intervalId = setInterval(loadMetrics, 10000);
});

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId);
});
</script>

<template>
  <header class="h-13 border-b border-dock-border bg-dock-surface flex items-center justify-between px-3.5 sm:px-6 shrink-0 z-10">
    <div class="flex items-center gap-2.5 min-w-0">
      <button
        @click="$emit('toggle-sidebar')"
        class="lg:hidden p-1.5 -ml-1 text-dock-text-muted hover:text-dock-text hover:bg-dock-panel rounded cursor-pointer"
        title="Abrir menu (ou arraste da esquerda para a direita)"
      >
        <Menu class="w-4 h-4" />
      </button>
      <div class="flex items-center gap-2 text-xs font-mono truncate">
        <span class="text-dock-text-dim hidden sm:inline">infra</span>
        <span class="text-dock-text-dim hidden sm:inline">/</span>
        <h1 class="text-sm font-sans font-semibold text-dock-text truncate">{{ pageTitle }}</h1>
      </div>
    </div>

    <div class="flex items-center gap-2 sm:gap-3">
      <!-- Botão Busca Rápida no Mobile/Topbar -->
      <button
        @click="$emit('open-palette')"
        class="p-1.5 sm:px-2.5 sm:py-1 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-xs font-mono text-dock-text-muted hover:text-dock-text flex items-center gap-1.5 transition-colors cursor-pointer"
        title="Busca Rápida (Ctrl+K)"
      >
        <Search class="w-3.5 h-3.5 text-dock-text-dim" />
        <span class="hidden sm:inline text-[11px]">Ctrl+K</span>
      </button>

      <!-- Escudo WAF Ativo -->
      <RouterLink
        to="/security"
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-dock-success/10 hover:bg-dock-success/20 border border-dock-success/30 text-[11px] font-mono text-dock-success transition-colors"
        title="WAF & Proteção Contra Ataques Ativa"
      >
        <ShieldCheck class="w-3.5 h-3.5 shrink-0" />
        <span class="hidden sm:inline">WAF Ativo</span>
      </RouterLink>
      <RouterLink
        v-if="canAccessDocker"
        to="/resources"
        class="hidden md:flex items-center gap-3 px-2.5 py-1 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border hover:border-dock-border-light text-xs font-mono transition-colors"
        title="Abrir Monitor de Recursos & Disco"
      >
        <div class="flex items-center gap-1.5">
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="sysInfo && (sysInfo.containers_running || 0) > 0 ? 'bg-dock-success' : 'bg-dock-text-dim'"
          ></span>
          <span class="text-dock-text-muted tabular-nums">
            {{ sysInfo?.containers_running || 0 }}/{{ sysInfo?.containers_count || 0 }} ativos
          </span>
        </div>
        <span class="text-dock-border">|</span>
        <span class="text-dock-text-muted tabular-nums">
          {{ sysInfo?.cpus || 0 }} vCPU
        </span>
        <span class="text-dock-border">|</span>
        <span class="text-dock-text-muted tabular-nums flex items-center gap-1">
          <HardDrive class="w-3 h-3 text-dock-text-dim" />
          {{ sysInfo?.memory_total_mb ? (sysInfo.memory_total_mb / 1024).toFixed(1) + ' GB RAM' : '--' }}
        </span>
      </RouterLink>

      <!-- Usuário Logado e Logout -->
      <div v-if="currentUser" class="flex items-center gap-2.5 pl-3 border-l border-dock-border">
        <div class="hidden sm:flex items-center gap-2 text-xs">
          <span class="font-mono text-dock-text">{{ currentUser.username }}</span>
          <span
            class="text-[10px] font-mono px-1.5 py-0.5 rounded border uppercase"
            :class="
              currentUser.role === 'admin'
                ? 'bg-dock-panel text-dock-text border-dock-border-light'
                : 'bg-dock-bg text-dock-text-dim border-dock-border'
            "
          >
            {{ currentUser.role }}
          </span>
        </div>
        <button
          @click="logout"
          class="p-1.5 text-dock-text-dim hover:text-dock-error hover:bg-dock-panel rounded transition-colors cursor-pointer"
          title="Encerrar sessão"
        >
          <LogOut class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </header>
</template>

