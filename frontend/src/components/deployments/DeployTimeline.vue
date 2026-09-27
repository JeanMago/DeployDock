<script setup lang="ts">
import { CheckCircle2, XCircle, Clock, RotateCcw } from 'lucide-vue-next';
import type { Deployment } from '@/services/types';

defineProps<{ deployments: Deployment[] }>();
defineEmits<{ (e: 'rollback', id: string): void }>();

const formatDate = (date: string) => new Date(date).toLocaleString();
</script>

<template>
  <div class="relative pl-6 border-l border-dock-border ml-4 space-y-8">
    <div v-for="dep in deployments" :key="dep.id" class="relative group">
      <div class="absolute -left-[33px] top-1 p-1 bg-dock-bg rounded-full border border-dock-border shadow-sm">
        <CheckCircle2 v-if="dep.status === 'success'" class="w-5 h-5 text-dock-success" />
        <XCircle v-else-if="dep.status === 'failed'" class="w-5 h-5 text-dock-error" />
        <Clock v-else class="w-5 h-5 text-dock-accent animate-pulse" />
      </div>
      <div class="glass-panel p-4 hover:border-dock-border-light transition-colors">
        <div class="flex justify-between items-start mb-2">
          <div>
            <h4 class="font-medium text-dock-text">{{ dep.commit_message || 'Manual Deployment' }}</h4>
            <div class="flex items-center gap-3 text-xs text-dock-text-muted mt-1">
              <span class="font-mono bg-dock-surface px-1.5 py-0.5 rounded border border-dock-border">{{ dep.commit_sha.substring(0,7) }}</span>
              <span>by {{ dep.author }}</span>
              <span>{{ formatDate(dep.started_at) }}</span>
            </div>
          </div>
          <button v-if="dep.status === 'success'" @click="$emit('rollback', dep.id)" class="px-2.5 py-1 text-xs font-medium bg-dock-surface border border-dock-border text-dock-text hover:bg-dock-accent/10 hover:text-dock-accent hover:border-dock-accent/30 rounded transition-colors flex items-center gap-1.5 opacity-0 group-hover:opacity-100">
            <RotateCcw class="w-3.5 h-3.5" /> Rollback
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
