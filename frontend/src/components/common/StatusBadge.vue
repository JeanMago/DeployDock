<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  status?: string | null;
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
}>(), {
  status: 'unknown',
  size: 'md',
  pulse: false
});

const config = computed(() => {
  const s = (props.status || 'unknown').toLowerCase();
  if (s.includes('running') || s.includes('success') || s.includes('up') || s.includes('healthy')) {
    return { color: 'bg-dock-success/10 text-dock-success border-dock-success/20', dot: 'bg-dock-success' };
  }
  if (s.includes('exited') || s.includes('stopped') || s.includes('failed')) {
    return { color: 'bg-dock-error/10 text-dock-error border-dock-error/20', dot: 'bg-dock-error' };
  }
  if (s.includes('paused') || s.includes('pending') || s.includes('warning')) {
    return { color: 'bg-dock-warning/10 text-dock-warning border-dock-warning/20', dot: 'bg-dock-warning' };
  }
  if (s.includes('restarting') || s.includes('progress') || s.includes('building') || s.includes('cloning') || s.includes('deploying')) {
    return { color: 'bg-dock-accent/10 text-dock-accent border-dock-accent/20', dot: 'bg-dock-accent' };
  }
  return { color: 'bg-dock-surface text-dock-text-muted border-dock-border', dot: 'bg-dock-text-dim' };
});

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm': return 'px-1.5 py-0.5 text-[10px] gap-1';
    case 'lg': return 'px-3 py-1.5 text-sm gap-2';
    default: return 'px-2 py-1 text-xs gap-1.5';
  }
});

const displayStatus = computed(() => {
  const s = (props.status || 'desconhecido').toLowerCase();
  const map: Record<string, string> = {
    running: 'em execução',
    healthy: 'saudável',
    success: 'sucesso',
    up: 'ativo',
    exited: 'parado',
    stopped: 'parado',
    failed: 'falhou',
    paused: 'pausado',
    pending: 'pendente',
    warning: 'alerta',
    restarting: 'reiniciando',
    building: 'compilando',
    cloning: 'clonando',
    deploying: 'implantando',
    rolled_back: 'revertido',
    unknown: 'desconhecido'
  };
  return map[s] || props.status || 'desconhecido';
});
</script>

<template>
  <span class="inline-flex items-center border rounded-full font-medium whitespace-nowrap capitalize transition-colors" :class="[config.color, sizeClasses]">
    <span 
      class="rounded-full shrink-0" 
      :class="[
        config.dot, 
        props.size === 'sm' ? 'w-1.5 h-1.5' : (props.size === 'lg' ? 'w-2.5 h-2.5' : 'w-2 h-2'),
        (pulse || (props.status && props.status.toLowerCase().includes('running'))) ? 'animate-pulse shadow-[0_0_8px_rgba(var(--color-dock-success),0.6)]' : ''
      ]"
    ></span>
    <slot>{{ displayStatus }}</slot>
  </span>
</template>
