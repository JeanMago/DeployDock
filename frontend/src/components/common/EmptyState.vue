<script setup lang="ts">
import type { Component } from 'vue';
defineProps<{
  icon: Component;
  title: string;
  description: string;
}>();
</script>
<template>
  <div class="flex flex-col items-center justify-center py-12 px-4 text-center glass-panel">
    <div class="w-10 h-10 rounded bg-dock-surface border border-dock-border flex items-center justify-center mb-3">
      <component :is="icon" class="w-5 h-5 text-dock-text-muted" />
    </div>
    <h3 class="text-sm font-semibold text-dock-text mb-1">{{ title }}</h3>
    <p class="text-xs text-dock-text-dim max-w-md mb-4">{{ description }}</p>
    <slot name="action"></slot>
  </div>
</template>

