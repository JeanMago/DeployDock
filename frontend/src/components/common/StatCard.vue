<script setup lang="ts">
import type { Component } from 'vue';
defineProps<{
  title: string;
  value: string | number;
  icon: Component;
  color?: string;
  trend?: string;
}>();
</script>

<template>
  <div class="glass-panel p-5 relative overflow-hidden group hover:-translate-y-1 transition-transform duration-300">
    <div class="absolute -right-4 -top-4 w-24 h-24 rounded-full opacity-10 blur-2xl group-hover:opacity-20 transition-opacity" :class="color || 'bg-dock-accent'"></div>
    <div class="flex justify-between items-start mb-4 relative z-10">
      <div class="p-2 rounded-lg bg-dock-surface border border-dock-border">
        <component :is="icon" class="w-5 h-5" :class="color ? `text-[${color}]` : 'text-dock-accent'" />
      </div>
      <span v-if="trend" class="text-xs font-medium px-2 py-1 rounded-full bg-dock-success/10 text-dock-success border border-dock-success/20">{{ trend }}</span>
    </div>
    <div class="relative z-10">
      <h4 class="text-dock-text-muted text-sm font-medium mb-1">{{ title }}</h4>
      <div class="text-3xl font-bold text-dock-text tracking-tight">{{ value }}</div>
    </div>
  </div>
</template>
