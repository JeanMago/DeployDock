<script setup lang="ts">
import type { Component } from 'vue';
defineProps<{
  icon: Component;
  title: string;
  description: string;
}>();
</script>
<template>
  <div class="flex flex-col items-center justify-center py-16 px-4 text-center glass-panel">
    <div class="w-16 h-16 rounded-full bg-dock-surface flex items-center justify-center mb-4 ring-8 ring-dock-surface/50">
      <component :is="icon" class="w-8 h-8 text-dock-text-dim" />
    </div>
    <h3 class="text-lg font-semibold text-dock-text mb-2">{{ title }}</h3>
    <p class="text-sm text-dock-text-muted max-w-sm mb-6">{{ description }}</p>
    <slot name="action"></slot>
  </div>
</template>
