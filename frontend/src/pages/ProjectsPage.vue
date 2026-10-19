<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import {
  Plus,
  Github,
  Rocket,
  Trash2,
  FolderGit2,
  ExternalLink,
  Globe,
  Settings2,
  KeyRound,
  FileText,
  Terminal,
  Activity,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { Project, ProjectHealthcheck } from '@/services/types';
import StatusBadge from '@/components/common/StatusBadge.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import CreateProjectModal from '@/components/projects/CreateProjectModal.vue';
import EditRoutingModal from '@/components/projects/EditRoutingModal.vue';
import ProjectEnvModal from '@/components/projects/ProjectEnvModal.vue';

const router = useRouter();
const projects = ref<Project[]>([]);
const loading = ref(true);
const showCreateModal = ref(false);
const editingProject = ref<Project | null>(null);
const envProject = ref<Project | null>(null);
const healthchecks = ref<Record<string, ProjectHealthcheck>>({});
const checkingHealth = ref<Record<string, boolean>>({});

const checkProjectHealth = async (id: string) => {
  checkingHealth.value[id] = true;
  try {
    healthchecks.value[id] = await api.projects.healthcheck(id);
  } catch {
    // ignore
  } finally {
    checkingHealth.value[id] = false;
  }
};

const checkAllHealth = async () => {
  await Promise.all(projects.value.map((p) => checkProjectHealth(p.id)));
};

const load = async () => {
  loading.value = true;
  try {
    projects.value = await api.projects.list();
    checkAllHealth();
  } catch (e) {
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
    alert(`Deploy do projeto "${name}" disparado. Acompanhe o progresso na aba Histórico de Deploys.`);
    load();
  } catch (err) {
    alert('Erro ao disparar deploy: ' + err);
  }
};

const openContainerTab = (project: Project, tab: 'logs' | 'exec') => {
  const cid = project.container_id || `deploydock_${project.name.toLowerCase()}`;
  router.push(`/containers/${cid}?tab=${tab}`);
};

const handleProjectCreated = () => {
  showCreateModal.value = false;
  load();
};

const handleProjectUpdated = () => {
  editingProject.value = null;
  load();
};
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-dock-border">
      <div>
        <h2 class="text-lg font-semibold text-dock-text">Projetos GitOps & 1-Click Apps</h2>
        <p class="text-xs text-dock-text-dim mt-0.5">
          Repositórios conectados, variáveis .env criptografadas, monitoramento HTTP e roteamento público
        </p>
      </div>
      <div class="flex items-center gap-2 self-start sm:self-auto">
        <button
          v-if="projects.length"
          @click="checkAllHealth"
          class="bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text px-3 py-2 rounded text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
          title="Testar resposta HTTP e latência de todas as aplicações"
        >
          <Activity class="w-3.5 h-3.5 text-dock-success" /> Testar Uptime HTTP
        </button>
        <button
          @click="showCreateModal = true"
          class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3.5 py-2 rounded text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
        >
          <Plus class="w-4 h-4" /> Novo Projeto
        </button>
      </div>
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
            class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3.5 py-2 rounded text-xs font-medium transition-colors flex items-center gap-1.5 mt-2 cursor-pointer"
          >
            <Plus class="w-4 h-4" /> Criar Primeiro Projeto
          </button>
        </template>
      </EmptyState>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="p in projects"
        :key="p.id"
        class="glass-panel p-4 flex flex-col justify-between hover:border-dock-border-light transition-colors space-y-3"
      >
        <div>
          <div class="flex justify-between items-start gap-2 mb-2">
            <div class="min-w-0 flex-1">
              <h3 class="font-semibold text-sm text-dock-text truncate" :title="p.name">
                {{ p.name }}
              </h3>
              <div
                class="flex items-center gap-1.5 text-xs text-dock-text-dim font-mono mt-0.5 truncate"
                :title="p.repo_url"
              >
                <Github v-if="p.repo_url.includes('github.com')" class="w-3.5 h-3.5 shrink-0" />
                <FolderGit2 v-else class="w-3.5 h-3.5 shrink-0 text-dock-text-muted" />
                <span class="truncate">{{ p.repo_url.replace('https://github.com/', '') }}</span>
              </div>
            </div>
            <StatusBadge :status="p.last_deploy_status || 'pendente'" size="sm" />
          </div>

          <!-- URL Pública + Status HTTP / Latência -->
          <div class="p-2 rounded bg-dock-bg border border-dock-border flex items-center justify-between gap-2">
            <div class="min-w-0 flex items-center gap-1.5 flex-1">
              <Globe class="w-3.5 h-3.5 text-dock-accent shrink-0" />
              <a
                :href="p.public_url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-xs font-mono text-dock-accent hover:underline truncate"
                :title="'Abrir ' + p.public_url"
              >
                {{ p.public_url }}
              </a>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              <button
                @click="checkProjectHealth(p.id)"
                class="px-1.5 py-0.5 rounded font-mono text-[10px] border cursor-pointer transition-colors"
                :class="
                  healthchecks[p.id]?.reachable
                    ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                    : healthchecks[p.id]
                    ? 'bg-dock-error/15 text-dock-error border-dock-error/30'
                    : 'bg-dock-surface text-dock-text-dim border-dock-border'
                "
                title="Clique para testar conectividade HTTP e latência"
              >
                <template v-if="checkingHealth[p.id]">...</template>
                <template v-else-if="healthchecks[p.id]?.reachable">
                  HTTP {{ healthchecks[p.id]?.status_code }} • {{ healthchecks[p.id]?.latency_ms }}ms
                </template>
                <template v-else-if="healthchecks[p.id]">
                  {{ healthchecks[p.id]?.status_code || 'OFF' }}
                </template>
                <template v-else>Ping</template>
              </button>
              <a
                :href="p.public_url"
                target="_blank"
                rel="noopener noreferrer"
                class="p-1 text-dock-text-muted hover:text-dock-text rounded hover:bg-dock-surface transition-colors"
                title="Abrir aplicação em nova aba"
              >
                <ExternalLink class="w-3.5 h-3.5" />
              </a>
              <button
                @click="editingProject = p"
                class="p-1 text-dock-text-muted hover:text-dock-text rounded hover:bg-dock-surface transition-colors cursor-pointer"
                title="Configurar Subdomínio / Domínio / Porta"
              >
                <Settings2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Barra de Ferramentas Rápidas do Projeto (Logs, Terminal, .env) -->
          <div class="grid grid-cols-3 gap-1.5 mt-2.5">
            <button
              @click="openContainerTab(p, 'logs')"
              class="px-2 py-1.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-[11px] font-mono text-dock-text-muted hover:text-dock-text flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              title="Ver logs da aplicação em tempo real"
            >
              <FileText class="w-3 h-3 text-dock-accent" /> Logs
            </button>
            <button
              @click="openContainerTab(p, 'exec')"
              class="px-2 py-1.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-[11px] font-mono text-dock-text-muted hover:text-dock-text flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              title="Abrir terminal de comandos no contêiner"
            >
              <Terminal class="w-3 h-3 text-dock-success" /> Shell
            </button>
            <button
              @click="envProject = p"
              class="px-2 py-1.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-[11px] font-mono text-dock-text-muted hover:text-dock-text flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              title="Variáveis de ambiente (.env) e Webhook"
            >
              <KeyRound class="w-3 h-3 text-dock-warning" /> .env
            </button>
          </div>
        </div>

        <!-- Rodapé do Card -->
        <div class="pt-3 border-t border-dock-border flex items-center justify-between">
          <span class="text-[11px] bg-dock-bg px-2 py-0.5 rounded border border-dock-border font-mono text-dock-text-dim">
            branch: {{ p.branch }}
          </span>
          <div class="flex items-center gap-1.5">
            <button
              @click="deploy(p.id, p.name)"
              class="px-2.5 py-1 text-xs font-mono text-dock-text bg-dock-surface hover:bg-dock-accent hover:text-white border border-dock-border rounded transition-colors flex items-center gap-1 cursor-pointer"
              title="Disparar novo Build & Deploy"
            >
              <Rocket class="w-3.5 h-3.5" /> Deploy
            </button>
            <button
              @click="deleteProject(p.id, p.name)"
              class="p-1.5 text-dock-text-dim hover:text-dock-error hover:bg-dock-error/10 bg-dock-surface border border-dock-border rounded transition-colors cursor-pointer"
              title="Excluir Projeto"
            >
              <Trash2 class="w-3.5 h-3.5" />
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

    <!-- Modal de Edição de Roteamento / URL -->
    <EditRoutingModal
      v-if="editingProject"
      :project="editingProject"
      @close="editingProject = null"
      @updated="handleProjectUpdated"
    />

    <!-- Modal de Variáveis de Ambiente (.env) & Webhook -->
    <ProjectEnvModal
      v-if="envProject"
      :project="envProject"
      @close="envProject = null"
    />
  </div>
</template>
