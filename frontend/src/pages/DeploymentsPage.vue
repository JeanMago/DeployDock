<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Rocket } from 'lucide-vue-next';
import DeployTimeline from '@/components/deployments/DeployTimeline.vue';
import DeployPipeline from '@/components/deployments/DeployPipeline.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import { api } from '@/services/api';
import type { Deployment } from '@/services/types';

const deployments = ref<Deployment[]>([]);
const loading = ref(true);

const load = async () => {
  loading.value = true;
  try { deployments.value = await api.deployments.list(); }
  catch(e) { console.error(e); }
  finally { loading.value = false; }
};

onMounted(load);

const handleRollback = async (id: string) => {
  if(confirm('Rollback to this deployment?')) {
    await api.deployments.rollback(id);
    load();
  }
};
</script>

<template>
  <div class="space-y-6 max-w-4xl mx-auto">
    <div class="glass-panel p-6 mb-8" v-if="deployments.length && deployments[0].status === 'in_progress'">
      <h3 class="text-sm font-medium text-dock-text-muted mb-4">Active Deployment</h3>
      <DeployPipeline :currentStep="2" status="in_progress" />
    </div>

    <div v-if="loading" class="flex justify-center py-20"><LoadingSpinner /></div>
    <div v-else-if="!deployments.length">
      <EmptyState :icon="Rocket" title="No deployments yet" description="Deployments will appear here once triggered." />
    </div>
    <div v-else>
      <DeployTimeline :deployments="deployments" @rollback="handleRollback" />
    </div>
  </div>
</template>
