<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { HardDrive, Server, Info, Trash2 } from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemInfo } from '@/services/types';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const sysInfo = ref<SystemInfo | null>(null);
const loading = ref(true);

const load = async () => {
  try { sysInfo.value = await api.system.info(); }
  catch(e) { console.error(e); }
  finally { loading.value = false; }
};

onMounted(load);

const prune = async () => {
  if(!confirm('Prune unused Docker data?')) return;
  const res = await api.system.prune();
  alert(`Reclaimed ${(res.reclaimed_space/1024/1024).toFixed(2)} MB`);
  load();
};
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <h2 class="text-xl font-bold text-dock-text mb-6">System Settings</h2>
    
    <div v-if="loading" class="flex justify-center py-10"><LoadingSpinner /></div>
    <div v-else-if="sysInfo" class="space-y-6">
      <div class="glass-panel p-6">
        <h3 class="flex items-center gap-2 font-semibold text-lg border-b border-dock-border pb-3 mb-4"><Server class="w-5 h-5 text-dock-accent"/> Docker Host Info</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-dock-surface p-3 rounded-lg border border-dock-border"><div class="text-xs text-dock-text-dim">OS</div><div class="font-medium truncate">{{ sysInfo.operating_system }}</div></div>
          <div class="bg-dock-surface p-3 rounded-lg border border-dock-border"><div class="text-xs text-dock-text-dim">Docker Version</div><div class="font-medium truncate">{{ sysInfo.server_version }}</div></div>
          <div class="bg-dock-surface p-3 rounded-lg border border-dock-border"><div class="text-xs text-dock-text-dim">CPUs</div><div class="font-medium truncate">{{ sysInfo.ncpu }}</div></div>
          <div class="bg-dock-surface p-3 rounded-lg border border-dock-border"><div class="text-xs text-dock-text-dim">Total Memory</div><div class="font-medium truncate">{{ (sysInfo.mem_total/1024/1024/1024).toFixed(2) }} GB</div></div>
        </div>
      </div>

      <div class="glass-panel p-6">
        <h3 class="flex items-center gap-2 font-semibold text-lg border-b border-dock-border pb-3 mb-4"><HardDrive class="w-5 h-5 text-dock-warning"/> Maintenance</h3>
        <p class="text-sm text-dock-text-muted mb-4">Clean up unused Docker images, containers, volumes, and networks to free up disk space.</p>
        <button @click="prune" class="bg-dock-surface hover:bg-dock-warning/10 text-dock-warning border border-dock-warning/30 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2">
          <Trash2 class="w-4 h-4" /> System Prune
        </button>
      </div>

      <div class="flex items-center justify-center text-xs text-dock-text-dim gap-2 mt-12">
        <Info class="w-4 h-4" /> DeployDock v0.1.0-beta
      </div>
    </div>
  </div>
</template>
