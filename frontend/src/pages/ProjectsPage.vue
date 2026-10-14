<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Plus, Github, Rocket, Trash2, FolderGit2 } from 'lucide-vue-next';
import { api } from '@/services/api';
import type { Project } from '@/services/types';
import StatusBadge from '@/components/common/StatusBadge.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import CreateProjectModal from '@/components/projects/CreateProjectModal.vue';

const projects = ref<Project[]>([]);
const loading = ref(true);
const showCreateModal = ref(false);

const load = async () => {
  loading.value = true;
  try { 
    projects.value = await api.projects.list(); 
  } catch(e) { 
    console.error(e); 
  } finally { 
    loading.value = false; 
  }
};

onMounted(load);

const deleteProject = async (id: string, name: string) => {
  if (!confirm(`Deseja realmente excluir o projeto "${name}"?`)) return;
  try {
    await api.projects.delete(id);
    load();
  } catch (err) {
    alert('Erro ao excluir projeto: ' + err);
  }
};

const deploy = async (id: string, name: string) => {
  try {
    await api.projects.triggerDeploy(id);
    alert(`Deploy do projeto "${name}" disparado com sucesso! Acompanhe na aba Deploys.`);
  } catch (err) {
    alert('Erro ao disparar deploy: ' + err);
  }
};

const handleProjectCreated = () => {
  showCreateModal.value = false;
  load();
};
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-xl font-bold text-dock-text">Projetos GitOps</h2>
        <p class="text-xs text-dock-text-dim mt-0.5">Gerencie seus repositórios e pipelines de entrega contínua</p>
      </div>
      <button 
        @click="showCreateModal = true"
        class="bg-dock-accent hover:bg-dock-accent-hover text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-dock-accent/20 flex items-center gap-2 cursor-pointer"
      >
        <Plus class="w-4 h-4" /> Novo Projeto
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-20"><LoadingSpinner /></div>
    <div v-else-if="!projects.length">
      <EmptyState 
        :icon="FolderGit2" 
        title="Nenhum projeto cadastrado" 
        description="Adicione um projeto diretamente pelo painel ou conecte um repositório Git para iniciar os deploys automatizados."
      >
        <template #action>
          <button 
            @click="showCreateModal = true"
            class="bg-dock-accent hover:bg-dock-accent-hover text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-dock-accent/20 flex items-center gap-2 mt-4 cursor-pointer"
          >
            <Plus class="w-4 h-4" /> Criar Primeiro Projeto
          </button>
        </template>
      </EmptyState>
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="p in projects" :key="p.id" class="glass-panel p-5 flex flex-col group hover:border-dock-border-light transition-all">
        <div class="flex justify-between items-start mb-4">
          <div class="min-w-0 flex-1 pr-2">
            <h3 class="font-bold text-lg text-dock-text truncate" :title="p.name">{{ p.name }}</h3>
            <div class="flex items-center gap-1.5 text-xs text-dock-text-muted mt-1 truncate" :title="p.repo_url">
              <Github v-if="p.repo_url.includes('github.com')" class="w-3.5 h-3.5 shrink-0" />
              <FolderGit2 v-else class="w-3.5 h-3.5 shrink-0 text-dock-accent" />
              <span class="truncate">{{ p.repo_url.replace('https://github.com/','') }}</span>
            </div>
          </div>
          <StatusBadge :status="p.last_deploy_status || 'pendente'" size="sm" />
        </div>
        
        <div class="mt-auto pt-4 border-t border-dock-border flex items-center justify-between">
          <span class="text-xs bg-dock-surface px-2 py-1 rounded-md border border-dock-border font-mono text-dock-text-dim">
            branch: {{ p.branch }}
          </span>
          <div class="flex items-center gap-1.5">
            <button 
              @click="deploy(p.id, p.name)" 
              class="p-1.5 text-dock-text-muted hover:text-dock-accent hover:bg-dock-accent/10 bg-dock-surface rounded transition-colors" 
              title="Disparar Deploy Agora"
            >
              <Rocket class="w-4 h-4"/>
            </button>
            <button 
              @click="deleteProject(p.id, p.name)" 
              class="p-1.5 text-dock-text-muted hover:text-dock-error hover:bg-dock-error/10 bg-dock-surface rounded transition-colors" 
              title="Excluir Projeto"
            >
              <Trash2 class="w-4 h-4"/>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Criação de Projeto -->
    <CreateProjectModal 
      v-if="showCreateModal" 
      @close="showCreateModal = false" 
      @created="handleProjectCreated" 
    />
  </div>
</template>
