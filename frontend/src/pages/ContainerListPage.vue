<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Grid, List, Search, RefreshCw, Box } from 'lucide-vue-next';
import ContainerCard from '@/components/containers/ContainerCard.vue';
import ContainerTable from '@/components/containers/ContainerTable.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import { api } from '@/services/api';
import type { Container } from '@/services/types';

const viewMode = ref<'grid' | 'table'>('grid');
const containers = ref<Container[]>([]);
const search = ref('');
const filter = ref('all');
const loading = ref(true);

const load = async () => {
  loading.value = true;
  try { containers.value = await api.containers.list(); }
  catch(e) { console.error(e); }
  finally { loading.value = false; }
};

onMounted(load);

const filtered = computed(() => {
  return containers.value.filter(c => {
    const mSearch = c.name.toLowerCase().includes(search.value.toLowerCase()) || c.image.toLowerCase().includes(search.value.toLowerCase());
    const mFilter = filter.value === 'all' || c.state === filter.value;
    return mSearch && mFilter;
  });
});

const handleAction = async (action: string, id: string) => {
  if (['stop','remove'].includes(action) && !confirm('Are you sure?')) return;
  try { await (api.containers as any)[action](id); load(); }
  catch(e) { alert(e); }
};
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row justify-between gap-4">
      <div class="flex items-center gap-3 glass-panel p-1 rounded-lg">
        <div class="relative w-64">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dock-text-dim" />
          <input v-model="search" type="text" placeholder="Search containers..." class="w-full bg-transparent border-none focus:ring-0 pl-9 pr-4 py-1.5 text-sm text-dock-text placeholder-dock-text-dim outline-none" />
        </div>
        <div class="w-px h-5 bg-dock-border"></div>
        <select v-model="filter" class="bg-transparent border-none text-sm text-dock-text focus:ring-0 outline-none pr-4 cursor-pointer">
          <option value="all" class="bg-dock-bg">All Status</option>
          <option value="running" class="bg-dock-bg">Running</option>
          <option value="exited" class="bg-dock-bg">Stopped</option>
        </select>
      </div>

      <div class="flex items-center gap-2">
        <button @click="load" class="p-2 glass-panel hover:bg-dock-surface text-dock-text-muted hover:text-dock-text transition-colors"><RefreshCw class="w-4 h-4" :class="{'animate-spin': loading}" /></button>
        <div class="flex glass-panel p-1 rounded-lg">
          <button @click="viewMode = 'grid'" class="p-1.5 rounded-md transition-colors" :class="viewMode === 'grid' ? 'bg-dock-surface text-dock-text' : 'text-dock-text-muted hover:text-dock-text'"><Grid class="w-4 h-4" /></button>
          <button @click="viewMode = 'table'" class="p-1.5 rounded-md transition-colors" :class="viewMode === 'table' ? 'bg-dock-surface text-dock-text' : 'text-dock-text-muted hover:text-dock-text'"><List class="w-4 h-4" /></button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-20"><LoadingSpinner /></div>
    <div v-else-if="!filtered.length">
      <EmptyState :icon="Box" title="No containers found" description="Try adjusting your search or filter criteria." />
    </div>
    <div v-else>
      <div v-if="viewMode === 'grid'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <ContainerCard v-for="c in filtered" :key="c.id" :container="c" @action="handleAction" />
      </div>
      <ContainerTable v-else :containers="filtered" @action="handleAction" />
    </div>
  </div>
</template>
