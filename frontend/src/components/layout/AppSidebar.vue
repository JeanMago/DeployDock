<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { LayoutDashboard, Box, FolderGit2, Rocket, Settings, ChevronLeft, Hexagon, BookOpen } from 'lucide-vue-next';
import { useAuth } from '@/composables/useAuth';

defineProps<{ isOpen: boolean }>();
defineEmits<{ (e: 'toggle'): void }>();

const route = useRoute();
const { canAccessDocker, isAdmin } = useAuth();

const navItems = computed(() => {
  const items = [
    { name: 'Painel', path: '/dashboard', icon: LayoutDashboard },
  ];

  // Contêineres exige permissão para acessar o Docker (admin ou developer)
  if (canAccessDocker.value) {
    items.push({ name: 'Contêineres', path: '/containers', icon: Box });
  }

  items.push(
    { name: 'Projetos', path: '/projects', icon: FolderGit2 },
    { name: 'Deploys', path: '/deployments', icon: Rocket },
    { name: 'Tutorial', path: '/tutorial', icon: BookOpen },
  );

  if (isAdmin.value) {
    items.push({ name: 'Configurações', path: '/settings', icon: Settings });
  }

  return items;
});
</script>

<template>
  <aside 
    :class="[
      'glass-panel m-4 flex flex-col transition-all duration-300 z-20',
      isOpen ? 'w-64' : 'w-20'
    ]"
  >
    <div class="h-16 flex items-center justify-between px-4 border-b border-dock-border">
      <div class="flex items-center gap-3 overflow-hidden whitespace-nowrap" v-if="isOpen">
        <Hexagon class="w-8 h-8 text-dock-accent" />
        <span class="font-bold text-lg tracking-tight bg-gradient-to-r from-dock-text to-dock-text-muted bg-clip-text text-transparent">DeployDock</span>
      </div>
      <div v-else class="flex justify-center w-full">
        <Hexagon class="w-8 h-8 text-dock-accent" />
      </div>
    </div>

    <nav class="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group"
        :class="route.path.startsWith(item.path) ? 'bg-dock-accent/10 text-dock-accent shadow-sm ring-1 ring-dock-accent/20' : 'text-dock-text-muted hover:bg-dock-surface hover:text-dock-text'"
      >
        <component :is="item.icon" class="w-5 h-5 shrink-0" :class="route.path.startsWith(item.path) ? 'text-dock-accent' : 'group-hover:text-dock-text'" />
        <span v-if="isOpen" class="font-medium text-sm">{{ item.name }}</span>
      </RouterLink>
    </nav>

    <div class="p-4 border-t border-dock-border flex items-center justify-between">
      <div v-if="isOpen" class="text-xs text-dock-text-dim">v0.1.0-beta</div>
      <button @click="$emit('toggle')" class="p-1.5 rounded-md text-dock-text-muted hover:text-dock-text hover:bg-dock-surface transition-colors">
        <ChevronLeft class="w-5 h-5 transition-transform duration-300" :class="{ 'rotate-180': !isOpen }" />
      </button>
    </div>
  </aside>
</template>
