<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Plus, Github, Rocket, Settings2, Trash2 } from 'lucide-vue-next';
import { api } from '@/services/api';
import type { Project } from '@/services/types';
import StatusBadge from '@/components/common/StatusBadge.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const projects = ref<Project[]>([]);
const loading = ref(true);

const load = async () => {
  loading.value = true;
  try { projects.value = await api.projects.list(); }
  catch(e) { console.error(e); }
  finally { loading.value = false; }
};

onMounted(load);

const deleteProject = async (id: string) => {
  if (!confirm('Delete this project?')) return;
  await api.projects.delete(id);
  load();
};

const deploy = async (id: string) => {
  await api.projects.triggerDeploy(id);
  alert('Deploy triggered');
};
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h2 class="text-xl font-bold text-dock-text">GitOps Projects</h2>
      <button class="bg-dock-accent hover:bg-dock-accent-hover text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-dock-accent/20 flex items-center gap-2">
        <Plus class="w-4 h-4" /> New Project
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-20"><LoadingSpinner /></div>
    <div v-else-if="!projects.length">
      <EmptyState :icon="Github" title="No projects yet" description="Connect a Git repository to start deploying automatically." />
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="p in projects" :key="p.id" class="glass-panel p-5 flex flex-col group hover:border-dock-border-light transition-all">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h3 class="font-bold text-lg text-dock-text">{{ p.name }}</h3>
            <div class="flex items-center gap-1.5 text-sm text-dock-text-muted mt-1">
              <Github class="w-4 h-4" /> <span class="truncate max-w-[200px]" :title="p.repo_url">{{ p.repo_url.replace('https://github.com/','') }}</span>
            </div>
          </div>
          <StatusBadge :status="p.last_deploy_status || 'pending'" size="sm" />
        </div>
        
        <div class="mt-auto pt-4 border-t border-dock-border flex items-center justify-between">
          <span class="text-xs bg-dock-surface px-2 py-1 rounded-md border border-dock-border font-mono">{{ p.branch }}</span>
          <div class="flex items-center gap-2">
            <button @click="deploy(p.id)" class="p-1.5 text-dock-text-muted hover:text-dock-accent bg-dock-surface rounded transition-colors" title="Deploy Now"><Rocket class="w-4 h-4"/></button>
            <button class="p-1.5 text-dock-text-muted hover:text-dock-text bg-dock-surface rounded transition-colors" title="Settings"><Settings2 class="w-4 h-4"/></button>
            <button @click="deleteProject(p.id)" class="p-1.5 text-dock-text-muted hover:text-dock-error bg-dock-surface rounded transition-colors" title="Delete"><Trash2 class="w-4 h-4"/></button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
