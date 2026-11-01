<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import {
  LayoutDashboard,
  Box,
  FolderGit2,
  Rocket,
  Layers,
  HardDrive,
  ShieldCheck,
  Settings,
  BookOpen,
  Terminal,
  LogOut,
  X,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-vue-next';
import { useAuth } from '@/composables/useAuth';

const props = defineProps<{
  isOpen: boolean;
  mobileOpen?: boolean;
  mobileDragTranslate?: number | null;
  isSwiping?: boolean;
}>();

defineEmits<{
  (e: 'toggle'): void;
  (e: 'close-mobile'): void;
  (e: 'open-palette'): void;
}>();

const route = useRoute();
const { currentUser, logout, canAccessDocker, isAdmin } = useAuth();

const navItems = computed(() => {
  const items = [
    { name: 'Visão Geral', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Projetos', path: '/projects', icon: FolderGit2 },
    { name: 'Deploys', path: '/deployments', icon: Rocket },
    { name: 'PaaS & Cloud', path: '/paas', icon: Layers },
  ];

  if (canAccessDocker.value) {
    items.push(
      { name: 'Contêineres', path: '/containers', icon: Box },
      { name: 'Recursos & Disco', path: '/resources', icon: HardDrive }
    );
  }

  items.push(
    { name: 'Segurança', path: '/security', icon: ShieldCheck },
    { name: 'Documentação', path: '/tutorial', icon: BookOpen }
  );

  if (isAdmin.value) {
    items.push({ name: 'Configurações', path: '/settings', icon: Settings });
  }

  return items;
});

const isRouteActive = (path: string) => route.path.startsWith(path);

const expanded = computed(() => props.isOpen || props.mobileOpen || props.isSwiping);

const mobileStyle = computed(() => {
  if (props.mobileDragTranslate !== null && props.mobileDragTranslate !== undefined) {
    return {
      transform: `translate3d(${props.mobileDragTranslate}px, 0, 0)`,
      transition: props.isSwiping ? 'none' : undefined,
    };
  }
  return undefined;
});
</script>

<template>
  <aside
    :style="mobileStyle"
    :class="[
      'h-screen bg-dock-surface border-r border-dock-border flex flex-col shrink-0 select-none',
      isSwiping ? '' : 'transition-all duration-200 ease-out',
      'fixed inset-y-0 left-0 z-40 w-[236px] shadow-2xl lg:shadow-none lg:static',
      mobileDragTranslate === null || mobileDragTranslate === undefined
        ? mobileOpen
          ? 'translate-x-0'
          : '-translate-x-full lg:translate-x-0'
        : 'lg:!transform-none',
      isOpen ? 'lg:w-52' : 'lg:w-14',
    ]"
  >
    <!-- Topo Limpo -->
    <div class="h-13 px-3.5 border-b border-dock-border flex items-center justify-between shrink-0">
      <div v-if="expanded" class="flex items-center gap-2.5 overflow-hidden">
        <div class="w-6 h-6 rounded bg-dock-panel border border-dock-border-light flex items-center justify-center text-dock-accent shrink-0">
          <Terminal class="w-3.5 h-3.5" />
        </div>
        <span class="font-semibold text-sm text-dock-text tracking-tight truncate">
          DeployDock
        </span>
      </div>

      <button
        @click="$emit('toggle')"
        class="hidden lg:flex p-1.5 rounded text-dock-text-dim hover:text-dock-text hover:bg-dock-panel transition-colors cursor-pointer"
        :class="{ 'mx-auto': !expanded }"
        :title="isOpen ? 'Recolher menu (Ctrl+B)' : 'Expandir menu (Ctrl+B)'"
      >
        <PanelLeftClose v-if="isOpen" class="w-4 h-4" />
        <PanelLeftOpen v-else class="w-4 h-4" />
      </button>

      <button
        @click="$emit('close-mobile')"
        class="lg:hidden p-1.5 rounded text-dock-text-muted hover:text-dock-text hover:bg-dock-panel cursor-pointer"
        title="Fechar menu"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Links de Navegação Minimalistas -->
    <nav class="flex-1 px-2.5 py-3 space-y-1 overflow-y-auto">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        :title="!expanded ? item.name : undefined"
        @click="$emit('close-mobile')"
        class="relative flex items-center gap-3 px-2.5 py-2 rounded-md text-xs transition-colors group"
        :class="[
          isRouteActive(item.path)
            ? 'bg-dock-panel text-dock-text font-medium'
            : 'text-dock-text-muted hover:bg-dock-panel/50 hover:text-dock-text',
          !expanded ? 'lg:justify-center lg:px-0' : '',
        ]"
      >
        <span
          v-if="isRouteActive(item.path)"
          class="absolute left-0 top-2 bottom-2 w-0.5 rounded-r bg-dock-accent"
        ></span>

        <component
          :is="item.icon"
          class="w-4 h-4 shrink-0 transition-colors"
          :class="
            isRouteActive(item.path)
              ? 'text-dock-accent'
              : 'text-dock-text-dim group-hover:text-dock-text'
          "
        />

        <span v-if="expanded" class="truncate">{{ item.name }}</span>
      </RouterLink>
    </nav>

    <!-- Rodapé Discreto -->
    <div v-if="currentUser" class="p-2.5 border-t border-dock-border shrink-0">
      <div v-if="expanded" class="flex items-center justify-between gap-2 px-1">
        <div class="flex items-center gap-2 min-w-0">
          <div class="w-6 h-6 rounded bg-dock-panel border border-dock-border flex items-center justify-center text-[10px] font-mono font-semibold text-dock-text uppercase shrink-0">
            {{ currentUser.username.slice(0, 2) }}
          </div>
          <span class="text-xs text-dock-text-muted truncate">
            {{ currentUser.username }}
          </span>
        </div>

        <button
          @click="logout"
          class="p-1.5 rounded text-dock-text-dim hover:text-dock-error hover:bg-dock-panel transition-colors cursor-pointer shrink-0"
          title="Sair"
        >
          <LogOut class="w-3.5 h-3.5" />
        </button>
      </div>

      <div v-else class="hidden lg:flex justify-center">
        <button
          @click="logout"
          class="p-1.5 rounded text-dock-text-dim hover:text-dock-error hover:bg-dock-panel transition-colors cursor-pointer"
          :title="`Sair (${currentUser.username})`"
        >
          <LogOut class="w-4 h-4" />
        </button>
      </div>
    </div>
  </aside>
</template>
