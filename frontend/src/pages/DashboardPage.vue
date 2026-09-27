<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Box, HardDrive, Cpu, Activity } from 'lucide-vue-next';
import StatCard from '@/components/common/StatCard.vue';
import ContainerTable from '@/components/containers/ContainerTable.vue';
import { api } from '@/services/api';
import type { SystemInfo, Container } from '@/services/types';

const sysInfo = ref<SystemInfo | null>(null);
const containers = ref<Container[]>([]);

onMounted(async () => {
  try {
    sysInfo.value = await api.system.info();
    const allC = await api.containers.list();
    containers.value = allC.slice(0, 5); // top 5 recent
  } catch (e) {
    console.error(e);
  }
});
</script>

<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard title="Total Containers" :value="sysInfo?.containers || 0" :icon="Box" color="dock-accent" />
      <StatCard title="Running" :value="sysInfo?.containers_running || 0" :icon="Activity" color="dock-success" />
      <StatCard title="Images" :value="sysInfo?.images || 0" :icon="HardDrive" color="dock-warning" />
      <StatCard title="System Memory" :value="sysInfo ? (sysInfo.mem_total / 1024/1024/1024).toFixed(1) + ' GB' : '0 GB'" :icon="Cpu" color="dock-info" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-dock-text">Recent Containers</h2>
          <RouterLink to="/containers" class="text-sm text-dock-accent hover:text-dock-accent-hover">View All</RouterLink>
        </div>
        <ContainerTable :containers="containers" @action="() => {}" />
      </div>
      <div class="space-y-4">
        <h2 class="text-lg font-semibold text-dock-text">Quick Actions</h2>
        <div class="glass-panel p-4 space-y-2">
          <button class="w-full text-left px-4 py-3 rounded-lg bg-dock-surface hover:bg-dock-surface/80 border border-dock-border transition-colors flex items-center gap-3">
            <Box class="w-5 h-5 text-dock-accent" /> <span>Deploy New Project</span>
          </button>
          <button class="w-full text-left px-4 py-3 rounded-lg bg-dock-surface hover:bg-dock-surface/80 border border-dock-border transition-colors flex items-center gap-3">
            <HardDrive class="w-5 h-5 text-dock-warning" /> <span>Prune System</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
