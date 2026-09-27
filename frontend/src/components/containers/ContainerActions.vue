<script setup lang="ts">
import { computed } from 'vue';
import { Play, Square, RotateCw, Trash2 } from 'lucide-vue-next';
import { api } from '@/services/api';

const props = defineProps<{ containerId: string; status: string }>();
const emit = defineEmits<{ (e: 'refresh'): void }>();

const isRunning = computed(() => props.status === 'running');

const doAction = async (action: 'start'|'stop'|'restart'|'remove') => {
  if ((action === 'stop' || action === 'remove') && !confirm(`Are you sure you want to ${action} this container?`)) return;
  try {
    await api.containers[action](props.containerId);
    emit('refresh');
  } catch (e) {
    alert(`Failed to ${action}: ` + e);
  }
};
</script>

<template>
  <div class="flex items-center gap-2">
    <button v-if="!isRunning" @click="doAction('start')" class="flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm bg-dock-surface text-dock-success hover:bg-dock-success/10 border border-dock-border"><Play class="w-4 h-4 mr-1"/> Start</button>
    <button v-if="isRunning" @click="doAction('stop')" class="flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm bg-dock-surface text-dock-warning hover:bg-dock-warning/10 border border-dock-border"><Square class="w-4 h-4 mr-1"/> Stop</button>
    <button @click="doAction('restart')" class="flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm bg-dock-surface text-dock-accent hover:bg-dock-accent/10 border border-dock-border"><RotateCw class="w-4 h-4 mr-1"/> Restart</button>
    <button @click="doAction('remove')" class="flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm bg-dock-surface text-dock-error hover:bg-dock-error/10 border border-dock-border ml-2"><Trash2 class="w-4 h-4 mr-1"/> Remove</button>
  </div>
</template>
