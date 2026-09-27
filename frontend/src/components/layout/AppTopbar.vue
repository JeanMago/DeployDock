<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { Bell, Menu } from 'lucide-vue-next';

defineEmits<{ (e: 'toggle-sidebar'): void }>();
const route = useRoute();

const pageTitle = computed(() => {
  return route.name?.toString().replace(/([A-Z])/g, ' $1').trim() || 'Dashboard';
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
          <span class="w-2 h-2 rounded-full bg-dock-success animate-pulse"></span>
          <span class="text-dock-text-muted">12 Running</span>
        </div>
        <div class="w-px h-4 bg-dock-border"></div>
        <div class="text-dock-text-muted">CPU: <span class="text-dock-text font-mono">14%</span></div>
        <div class="w-px h-4 bg-dock-border"></div>
        <div class="text-dock-text-muted">RAM: <span class="text-dock-text font-mono">42%</span></div>
      </div>

      <button class="p-2 text-dock-text-muted hover:text-dock-accent hover:bg-dock-accent/10 rounded-full transition-colors relative">
        <Bell class="w-5 h-5" />
        <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-dock-accent rounded-full border-2 border-dock-bg"></span>
      </button>
    </div>
  </header>
</template>
