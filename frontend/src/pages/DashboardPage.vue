<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Box, HardDrive, Cpu, Activity, Plus, Trash2 } from 'lucide-vue-next';
import StatCard from '@/components/common/StatCard.vue';
import ContainerTable from '@/components/containers/ContainerTable.vue';
import CreateProjectModal from '@/components/projects/CreateProjectModal.vue';
import { api } from '@/services/api';
import type { SystemInfo, Container } from '@/services/types';
import { useAuth } from '@/composables/useAuth';

const router = useRouter();
const { canAccessDocker } = useAuth();
const sysInfo = ref<SystemInfo | null>(null);
const containers = ref<Container[]>([]);
const showCreateModal = ref(false);

const load = async () => {
  if (canAccessDocker.value) {
    try {
      sysInfo.value = await api.system.info();
      const allC = await api.containers.list();
      containers.value = allC.slice(0, 5); // top 5 recentes
    } catch (e) {
      console.error(e);
    }
  }
};

onMounted(load);

const handleContainerAction = async (action: string, id: string) => {
  if (['stop', 'remove'].includes(action) && !confirm('Deseja realmente executar esta ação?')) return;
  try {
    await (api.containers as any)[action](id);
    load();
  } catch (e) {
    alert('Erro: ' + e);
  }
};

const prune = async () => {
  if (!confirm('Deseja limpar dados não utilizados do Docker (imagens, contêineres e volumes parados)?')) return;
  try {
    const res = await api.system.prune();
    const mb = (res.reclaimed_space / (1024 * 1024)).toFixed(2);
    alert(`Limpeza concluída! ${mb} MB liberados.`);
    load();
  } catch (e) {
    alert('Erro ao executar limpeza: ' + e);
  }
};

const handleProjectCreated = () => {
  showCreateModal.value = false;
  router.push('/projects');
};
</script>

<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard title="Total de Contêineres" :value="sysInfo?.containers_count || 0" :icon="Box" color="dock-accent" />
      <StatCard title="Em Execução" :value="sysInfo?.containers_running || 0" :icon="Activity" color="dock-success" />
      <StatCard title="Imagens Docker" :value="sysInfo?.images_count || 0" :icon="HardDrive" color="dock-warning" />
      <StatCard title="Memória do Sistema" :value="sysInfo?.memory_total_mb ? (sysInfo.memory_total_mb / 1024).toFixed(1) + ' GB' : '0 GB'" :icon="Cpu" color="dock-info" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div v-if="canAccessDocker" class="lg:col-span-2 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-dock-text">Contêineres Recentes</h2>
            <p class="text-xs text-dock-text-dim">Instâncias gerenciadas pelo Docker Engine</p>
          </div>
          <RouterLink to="/containers" class="text-sm text-dock-accent hover:text-dock-accent-hover font-medium">Ver Todos →</RouterLink>
        </div>
        <ContainerTable :containers="containers" @action="handleContainerAction" />
      </div>
      <div v-else class="lg:col-span-2 glass-panel p-8 text-center flex flex-col items-center justify-center">
        <div class="p-3 bg-dock-surface rounded-xl border border-dock-border mb-3 text-dock-accent">
          <Box class="w-8 h-8" />
        </div>
        <h3 class="text-base font-semibold text-dock-text">Gerenciamento Docker Restrito</h3>
        <p class="text-xs text-dock-text-dim max-w-md mt-1">
          Seu perfil possui permissão somente de leitura de projetos e deploys. Para visualizar e interagir com os contêineres Docker, solicite a um administrador o papel de <strong>developer</strong> ou <strong>admin</strong>.
        </p>
      </div>

      <div class="space-y-4">
        <h2 class="text-lg font-semibold text-dock-text">Ações Rápidas</h2>
        <div class="glass-panel p-4 space-y-2">
          <button 
            @click="showCreateModal = true"
            class="w-full text-left px-4 py-3 rounded-lg bg-dock-surface hover:bg-dock-surface/80 border border-dock-border transition-colors flex items-center gap-3 cursor-pointer group"
          >
            <div class="p-2 rounded-lg bg-dock-accent/10 text-dock-accent group-hover:scale-105 transition-transform">
              <Plus class="w-5 h-5" />
            </div>
            <div>
              <div class="font-medium text-sm text-dock-text">Adicionar Novo Projeto</div>
              <div class="text-xs text-dock-text-dim">Criar projeto diretamente ou conectar Git</div>
            </div>
          </button>
          <button 
            @click="prune"
            class="w-full text-left px-4 py-3 rounded-lg bg-dock-surface hover:bg-dock-surface/80 border border-dock-border transition-colors flex items-center gap-3 cursor-pointer group"
          >
            <div class="p-2 rounded-lg bg-dock-warning/10 text-dock-warning group-hover:scale-105 transition-transform">
              <Trash2 class="w-5 h-5" />
            </div>
            <div>
              <div class="font-medium text-sm text-dock-text">Limpeza do Sistema</div>
              <div class="text-xs text-dock-text-dim">Liberar espaço em disco (Prune)</div>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Novo Projeto -->
    <CreateProjectModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="handleProjectCreated"
    />
  </div>
</template>
