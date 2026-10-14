<script setup lang="ts">
import { computed } from 'vue';
import { Play, Square, RotateCw, Trash2 } from 'lucide-vue-next';
import { api } from '@/services/api';

const props = defineProps<{ containerId: string; status?: string | null }>();
const emit = defineEmits<{ (e: 'refresh'): void }>();

const isRunning = computed(() => props.status === 'running');

const doAction = async (action: 'start'|'stop'|'restart'|'remove') => {
  const actionLabels = {
    start: 'iniciar',
    stop: 'parar',
    restart: 'reiniciar',
    remove: 'remover'
  };
  const label = actionLabels[action];
  if ((action === 'stop' || action === 'remove') && !confirm(`Deseja realmente ${label} este contêiner?`)) return;
  try {
    await api.containers[action](props.containerId);
    emit('refresh');
  } catch (e) {
    alert(`Erro ao ${label} contêiner: ` + e);
  }
};
</script>

<template>
  <div class="flex items-center gap-2">
    <button v-if="!isRunning" @click="doAction('start')" class="flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm bg-dock-surface text-dock-success hover:bg-dock-success/10 border border-dock-border cursor-pointer"><Play class="w-4 h-4 mr-1"/> Iniciar</button>
    <button v-if="isRunning" @click="doAction('stop')" class="flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm bg-dock-surface text-dock-warning hover:bg-dock-warning/10 border border-dock-border cursor-pointer"><Square class="w-4 h-4 mr-1"/> Parar</button>
    <button @click="doAction('restart')" class="flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm bg-dock-surface text-dock-accent hover:bg-dock-accent/10 border border-dock-border cursor-pointer"><RotateCw class="w-4 h-4 mr-1"/> Reiniciar</button>
    <button @click="doAction('remove')" class="flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm bg-dock-surface text-dock-error hover:bg-dock-error/10 border border-dock-border ml-2 cursor-pointer"><Trash2 class="w-4 h-4 mr-1"/> Remover</button>
  </div>
</template>
