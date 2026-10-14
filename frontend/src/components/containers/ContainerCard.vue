<script setup lang="ts">
import { useRouter } from 'vue-router';
import { Play, Square, RotateCw, Trash2, HardDrive, Cpu } from 'lucide-vue-next';
import StatusBadge from '@/components/common/StatusBadge.vue';
import type { Container } from '@/services/types';

const props = defineProps<{ container: Container }>();
const emit = defineEmits<{ (e: 'action', type: string, id: string): void }>();
const router = useRouter();


const navigate = () => router.push(`/containers/${props.container.id}`);
</script>

<template>
  <div class="glass-panel p-5 hover:border-dock-border-light transition-all group cursor-pointer flex flex-col h-full" @click="navigate">
    <div class="flex justify-between items-start mb-3">
      <div class="min-w-0 flex-1 pr-4">
        <div class="flex items-center gap-2 mb-1">
          <h3 class="font-semibold text-lg text-dock-text truncate" :title="container.name">{{ container.name }}</h3>
          <StatusBadge :status="container.state" size="sm" />
        </div>
        <p class="text-xs text-dock-text-dim font-mono truncate" :title="container.image">{{ container.image }}</p>
      </div>
    </div>
    
    <div class="mt-auto pt-4 flex items-center justify-between border-t border-dock-border/50">
      <div class="flex gap-3 text-xs text-dock-text-muted">
        <span class="flex items-center gap-1"><Cpu class="w-3.5 h-3.5"/> --</span>
        <span class="flex items-center gap-1"><HardDrive class="w-3.5 h-3.5"/> --</span>
      </div>
      <div class="flex items-center gap-1.5" @click.stop>
        <button v-if="container.state !== 'running'" @click="emit('action', 'start', container.id)" class="p-1.5 text-dock-text-muted hover:text-dock-success rounded bg-dock-surface hover:bg-dock-success/10 transition-colors cursor-pointer" title="Iniciar">
          <Play class="w-4 h-4" />
        </button>
        <button v-if="container.state === 'running'" @click="emit('action', 'stop', container.id)" class="p-1.5 text-dock-text-muted hover:text-dock-warning rounded bg-dock-surface hover:bg-dock-warning/10 transition-colors cursor-pointer" title="Parar">
          <Square class="w-4 h-4" />
        </button>
        <button @click="emit('action', 'restart', container.id)" class="p-1.5 text-dock-text-muted hover:text-dock-accent rounded bg-dock-surface hover:bg-dock-accent/10 transition-colors cursor-pointer" title="Reiniciar">
          <RotateCw class="w-4 h-4" />
        </button>
        <button @click="emit('action', 'remove', container.id)" class="p-1.5 text-dock-text-muted hover:text-dock-error rounded bg-dock-surface hover:bg-dock-error/10 transition-colors ml-1 cursor-pointer" title="Remover">
          <Trash2 class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>
