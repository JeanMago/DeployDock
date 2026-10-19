<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, RouterLink } from 'vue-router';
import { Box, HardDrive, Cpu, Activity, Plus, Trash2, Server } from 'lucide-vue-next';
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
      containers.value = allC.slice(0, 6);
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
    const res = await api.system.prune('all');
    const mb = (res.space_reclaimed_mb ?? (res.reclaimed_space || 0) / (1024 * 1024)).toFixed(2);
    alert(`Limpeza concluída: ${mb} MB liberados.`);
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
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="Contêineres Totais"
        :value="sysInfo?.containers_count || 0"
        :subtitle="`${sysInfo?.containers_stopped || 0} parados`"
        :icon="Box"
      />
      <StatCard
        title="Em Execução"
        :value="sysInfo?.containers_running || 0"
        subtitle="ativos agora"
        :icon="Activity"
      />
      <StatCard
        title="Imagens Locais"
        :value="sysInfo?.images_count || 0"
        :subtitle="`${sysInfo?.volumes_count || 0} volumes`"
        :icon="HardDrive"
      />
      <StatCard
        title="Capacidade do Host"
        :value="sysInfo?.memory_total_mb ? (sysInfo.memory_total_mb / 1024).toFixed(1) + ' GB' : '0 GB'"
        :subtitle="`${sysInfo?.cpus || 0} vCPUs`"
        :icon="Cpu"
      />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div v-if="canAccessDocker" class="lg:col-span-2 space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-sm font-semibold text-dock-text">Contêineres</h2>
            <p class="text-xs text-dock-text-dim">Instâncias em execução e recentes no Docker Engine</p>
          </div>
          <RouterLink to="/containers" class="text-xs font-mono text-dock-accent hover:underline">
            ver todos →
          </RouterLink>
        </div>
        <ContainerTable :containers="containers" @action="handleContainerAction" />
      </div>
      <div v-else class="lg:col-span-2 glass-panel p-8 text-center flex flex-col items-center justify-center">
        <div class="p-2.5 bg-dock-surface rounded border border-dock-border mb-3 text-dock-text-muted">
          <Box class="w-6 h-6" />
        </div>
        <h3 class="text-sm font-semibold text-dock-text">Gerenciamento Docker Restrito</h3>
        <p class="text-xs text-dock-text-dim max-w-md mt-1">
          Seu perfil possui permissão somente de leitura de projetos e deploys. Para visualizar e interagir com os contêineres Docker, solicite permissão <strong>developer</strong> ou <strong>admin</strong>.
        </p>
      </div>

      <div class="space-y-3">
        <div>
          <h2 class="text-sm font-semibold text-dock-text">Operações do Sistema</h2>
          <p class="text-xs text-dock-text-dim">Atalhos de provisionamento e manutenção</p>
        </div>
        <div class="glass-panel p-3 space-y-2">
          <button
            @click="showCreateModal = true"
            class="w-full text-left px-3 py-2.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border hover:border-dock-border-light transition-colors flex items-center gap-3 cursor-pointer"
          >
            <div class="p-1.5 rounded bg-dock-panel border border-dock-border text-dock-text">
              <Plus class="w-4 h-4" />
            </div>
            <div>
              <div class="font-medium text-xs text-dock-text">Novo Projeto GitOps</div>
              <div class="text-[11px] text-dock-text-dim">Implantar via repositório Git ou template</div>
            </div>
          </button>

          <RouterLink
            v-if="canAccessDocker"
            to="/resources"
            class="w-full text-left px-3 py-2.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border hover:border-dock-border-light transition-colors flex items-center gap-3"
          >
            <div class="p-1.5 rounded bg-dock-panel border border-dock-border text-dock-text">
              <Server class="w-4 h-4" />
            </div>
            <div>
              <div class="font-medium text-xs text-dock-text">Monitor de Recursos & Disco</div>
              <div class="text-[11px] text-dock-text-dim">Ver uso real do host vs. Docker e limpar disco</div>
            </div>
          </RouterLink>

          <button
            v-if="canAccessDocker"
            @click="prune"
            class="w-full text-left px-3 py-2.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border hover:border-dock-border-light transition-colors flex items-center gap-3 cursor-pointer"
          >
            <div class="p-1.5 rounded bg-dock-panel border border-dock-border text-dock-text-muted">
              <Trash2 class="w-4 h-4" />
            </div>
            <div>
              <div class="font-medium text-xs text-dock-text">Limpeza Rápida (Docker Prune)</div>
              <div class="text-[11px] text-dock-text-dim">Remover imagens e contêineres sem uso</div>
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

