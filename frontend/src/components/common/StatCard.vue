<script setup lang="ts">
import type { Component } from 'vue';
defineProps<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: Component;
  color?: string;
  trend?: string;
}>();
</script>

<template>
  <div class="glass-panel p-4 flex flex-col justify-between">
    <div class="flex items-center justify-between text-xs text-dock-text-muted mb-2">
      <span class="font-medium">{{ title }}</span>
      <component :is="icon" class="w-4 h-4 text-dock-text-dim shrink-0" />
    </div>
    <div class="flex items-baseline justify-between gap-2">
      <div class="text-2xl font-mono font-semibold text-dock-text tracking-tight tabular-nums">
        {{ value }}
      </div>
      <span
        v-if="trend || subtitle"
        class="text-[11px] font-mono text-dock-text-dim truncate"
      >
        {{ trend || subtitle }}
      </span>
    </div>
  </div>
</template>

