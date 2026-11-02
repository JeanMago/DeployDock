<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
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
  GitBranch,
  Lock,
  Cpu,
  ShieldCheck,
  Layers,
  Users,
  X,
  Square,
  Play,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { Project, ProjectHealthcheck, ProjectPreview, ProjectMember } from '@/services/types';
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
const totalAutoHeals = ref(0);

// Estado do Modal de Preview Deployments (Branch / PR)
const previewProject = ref<Project | null>(null);
const previewsList = ref<ProjectPreview[]>([]);
const loadingPreviews = ref(false);
const creatingPreview = ref(false);
const newPreviewBranch = ref('feat-nova-interface');

// Estado do Modal de Escalonamento Horizontal (Réplicas + Autoscaling) & RBAC por Projeto
const scaleProject = ref<Project | null>(null);
const scaleForm = ref({
  replicas: 1,
  autoscale_enabled: false,
  autoscale_min_replicas: 1,
  autoscale_max_replicas: 3,
  autoscale_cpu_target: 75,
  auto_heal: true,
});
const savingScale = ref(false);
const projectMembers = ref<ProjectMember[]>([]);
const memberForm = ref({ username: '', role: 'developer' as 'admin' | 'developer' | 'viewer' });
const projectActionLoading = ref<Record<string, boolean>>({});

const stopProject = async (p: Project) => {
  if (!confirm(`Deseja realmente interromper o projeto "${p.name}"? Seus contêineres serão parados e o Auto-Heal permanecerá pausado.`)) return;
  projectActionLoading.value[p.id] = true;
  try {
    await api.projects.stop(p.id);
    await loadUptimeOverview(true);
    await load();
  } catch (err: any) {
    alert(err?.message || 'Erro ao parar projeto');
  } finally {
    projectActionLoading.value[p.id] = false;
  }
};

const startProject = async (p: Project) => {
  projectActionLoading.value[p.id] = true;
  try {
    await api.projects.start(p.id);
    await loadUptimeOverview(true);
    await load();
  } catch (err: any) {
    alert(err?.message || 'Erro ao iniciar projeto');
  } finally {
    projectActionLoading.value[p.id] = false;
  }
};

const toggleAutoHeal = async (p: Project) => {
  try {
    const res = await api.projects.toggleAutoHeal(p.id);
    p.auto_heal = res.auto_heal;
  } catch (err: any) {
    alert(err?.message || 'Erro ao alterar Auto-Heal');
  }
};

const openScaleAndRbacModal = async (p: Project) => {
  scaleProject.value = p;
  scaleForm.value = {
    replicas: p.replicas || 1,
    autoscale_enabled: !!p.autoscale_enabled,
    autoscale_min_replicas: p.autoscale_min_replicas || 1,
    autoscale_max_replicas: p.autoscale_max_replicas || 3,
    autoscale_cpu_target: p.autoscale_cpu_target || 75,
    auto_heal: p.auto_heal !== false,
  };
  try {
    projectMembers.value = await api.projects.listMembers(p.id);
  } catch {
    projectMembers.value = [];
  }
};

const handleSaveScale = async () => {
  if (!scaleProject.value) return;
  savingScale.value = true;
  try {
    await api.projects.scale(scaleProject.value.id, scaleForm.value);
    await load();
    alert('Escalonamento horizontal e política de Autoscaling atualizados!');
  } catch (e: any) {
    alert(e?.message || 'Erro ao escalar réplicas do projeto.');
  } finally {
    savingScale.value = false;
  }
};

const handleAddProjectMember = async () => {
  if (!scaleProject.value || !memberForm.value.username.trim()) return;
  try {
    await api.projects.addMember(scaleProject.value.id, {
      username: memberForm.value.username.trim(),
      role: memberForm.value.role,
    });
    memberForm.value.username = '';
    projectMembers.value = await api.projects.listMembers(scaleProject.value.id);
  } catch (e: any) {
    alert(e?.message || 'Erro ao adicionar membro RBAC ao projeto.');
  }
};

const handleRemoveProjectMember = async (userId: string) => {
  if (!scaleProject.value) return;
  try {
    await api.projects.removeMember(scaleProject.value.id, userId);
    projectMembers.value = await api.projects.listMembers(scaleProject.value.id);
  } catch (e: any) {
    alert(e?.message || 'Erro ao remover membro do projeto.');
  }
};

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

const loadUptimeOverview = async (forceNow: boolean = false) => {
  try {
    const res = forceNow
      ? await api.projects.uptimeCheckNow()
      : await api.projects.uptimeOverview();
    totalAutoHeals.value = res.total_auto_heals || 0;
    if (res.projects) {
      healthchecks.value = { ...healthchecks.value, ...res.projects };
    }
  } catch {
    await Promise.all(projects.value.map((p) => checkProjectHealth(p.id)));
  }
};

const load = async () => {
  loading.value = true;
  try {
    projects.value = await api.projects.list();
    await loadUptimeOverview(false);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

let uptimeTimer: ReturnType<typeof setInterval> | null = null;
onMounted(() => {
  load();
  uptimeTimer = setInterval(() => loadUptimeOverview(false), 15000);
});

onUnmounted(() => {
  if (uptimeTimer) clearInterval(uptimeTimer);
});

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

const openPreviewsModal = async (project: Project) => {
  previewProject.value = project;
  loadingPreviews.value = true;
  try {
    previewsList.value = await api.projects.listPreviews(project.id);
  } catch {
    previewsList.value = [];
  } finally {
    loadingPreviews.value = false;
  }
};

const handleCreatePreview = async () => {
  if (!previewProject.value || !newPreviewBranch.value.trim()) return;
  creatingPreview.value = true;
  try {
    await api.projects.createPreview(previewProject.value.id, newPreviewBranch.value.trim());
    previewsList.value = await api.projects.listPreviews(previewProject.value.id);
    newPreviewBranch.value = '';
  } catch (e: any) {
    alert(e?.message || 'Erro ao criar ambiente de Preview.');
  } finally {
    creatingPreview.value = false;
  }
};

const handleDeletePreview = async (branchSlug: string) => {
  if (!previewProject.value) return;
  try {
    await api.projects.deletePreview(previewProject.value.id, branchSlug);
    previewsList.value = await api.projects.listPreviews(previewProject.value.id);
  } catch (e: any) {
    alert(e?.message || 'Erro ao encerrar Preview.');
  }
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
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-lg font-semibold text-dock-text">Projetos GitOps & 1-Click Apps</h2>
          <span
            class="text-[11px] font-mono px-2 py-0.5 rounded bg-dock-success/10 border border-dock-success/30 text-dock-success flex items-center gap-1"
          >
            <ShieldCheck class="w-3 h-3" /> Uptime & Auto-Heal Ativos ({{ totalAutoHeals }} recuperações)
          </span>
        </div>
        <p class="text-xs text-dock-text-dim mt-0.5">
          Repositórios públicos/privados, Preview Environments por Branch/PR, Quotas de CPU/RAM e monitoramento HTTP contínuo
        </p>
      </div>
      <div class="flex items-center gap-2 self-start sm:self-auto">
        <button
          v-if="projects.length"
          @click="loadUptimeOverview(true)"
          class="bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text px-3 py-2 rounded text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
          title="Testar resposta HTTP e latência de todas as aplicações agora"
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
        <div class="space-y-2.5">
          <div class="flex justify-between items-start gap-2">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5">
                <h3 class="font-semibold text-sm text-dock-text truncate" :title="p.name">
                  {{ p.name }}
                </h3>
                <Lock
                  v-if="p.has_git_token"
                  class="w-3 h-3 text-dock-accent shrink-0"
                  title="Repositório Privado autenticado via Token PAT (Fernet AES-128)"
                />
              </div>
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
                title="Configurar Subdomínio / Quotas CPU & RAM / Token Git"
              >
                <Settings2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Monitor de Uptime (%) + Sparkline de Histórico de Latência -->
          <div
            v-if="healthchecks[p.id]"
            class="px-2.5 py-2 rounded bg-dock-bg/60 border border-dock-border flex items-center justify-between gap-2 text-[11px] font-mono"
          >
            <div class="flex items-center gap-2">
              <span
                :class="
                  (healthchecks[p.id]?.uptime_percent ?? 100) >= 95
                    ? 'text-dock-success'
                    : 'text-dock-warning'
                "
              >
                Uptime: {{ healthchecks[p.id]?.uptime_percent ?? 100 }}%
              </span>
              <span class="text-dock-text-dim">•</span>
              <span class="text-dock-text-muted">
                Méd: {{ healthchecks[p.id]?.avg_latency_ms ?? healthchecks[p.id]?.latency_ms }}ms
              </span>
            </div>

            <!-- Sparkline de barras das últimas medições HTTP -->
            <div
              v-if="healthchecks[p.id]?.history?.length"
              class="flex items-end gap-0.5 h-4"
              title="Histórico recente de latência HTTP"
            >
              <span
                v-for="(pt, idx) in (healthchecks[p.id]?.history || []).slice(-14)"
                :key="idx"
                class="w-1 rounded-xs transition-all"
                :class="pt.ok ? 'bg-dock-success' : 'bg-dock-error'"
                :style="{ height: `${Math.max(25, Math.min(100, Math.round(pt.latency_ms / 1.5)))}%` }"
                :title="`${pt.latency_ms}ms (HTTP ${pt.status_code})`"
              ></span>
            </div>
          </div>

          <!-- Badges de Quotas de CPU/RAM, Réplicas e Auto-Heal -->
          <div
            class="flex flex-wrap items-center gap-1.5 text-[10px] font-mono"
          >
            <button
              @click="openScaleAndRbacModal(p)"
              class="px-2 py-0.5 rounded bg-dock-accent/15 hover:bg-dock-accent/25 border border-dock-accent/30 text-dock-accent flex items-center gap-1 cursor-pointer"
              title="Configurar Escalonamento Horizontal (Réplicas), Autoscaling e Membros RBAC"
            >
              <Layers class="w-3 h-3" />
              {{ p.replicas || 1 }} {{ (p.replicas || 1) > 1 ? 'Réplicas' : 'Réplica' }}
              <span v-if="p.autoscale_enabled">• Auto ({{ p.autoscale_min_replicas }}-{{ p.autoscale_max_replicas }})</span>
            </button>
            <span
              v-if="p.memory_limit_mb || p.cpu_limit_cores"
              class="px-2 py-0.5 rounded bg-dock-surface border border-dock-border text-dock-accent flex items-center gap-1"
            >
              <Cpu class="w-3 h-3" />
              {{ p.memory_limit_mb ? `${p.memory_limit_mb}MB` : 'RAM Livre' }} /
              {{ p.cpu_limit_cores ? `${p.cpu_limit_cores} vCPU` : 'CPU Livre' }}
            </span>
            <button
              @click="toggleAutoHeal(p)"
              :class="[
                'px-2 py-0.5 rounded border transition-colors flex items-center gap-1 cursor-pointer',
                p.auto_heal !== false
                  ? 'bg-dock-success/10 border-dock-success/30 text-dock-success hover:bg-dock-success/20'
                  : 'bg-dock-surface border-dock-border text-dock-text-dim hover:text-dock-text'
              ]"
              :title="p.auto_heal !== false ? 'Auto-Heal Ativo (clique para pausar)' : 'Auto-Heal Desativado (clique para ativar)'"
            >
              <ShieldCheck class="w-3 h-3" />
              Auto-Heal: {{ p.auto_heal !== false ? 'ON' : 'OFF' }}
            </button>
          </div>

          <!-- Barra de Ferramentas Rápidas do Projeto (Logs, Terminal, .env, Previews) -->
          <div class="grid grid-cols-4 gap-1.5 pt-0.5">
            <button
              @click="openContainerTab(p, 'logs')"
              class="px-2 py-1.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-[11px] font-mono text-dock-text-muted hover:text-dock-text flex items-center justify-center gap-1 transition-colors cursor-pointer"
              title="Ver logs da aplicação em tempo real"
            >
              <FileText class="w-3 h-3 text-dock-accent" /> Logs
            </button>
            <button
              @click="openContainerTab(p, 'exec')"
              class="px-2 py-1.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-[11px] font-mono text-dock-text-muted hover:text-dock-text flex items-center justify-center gap-1 transition-colors cursor-pointer"
              title="Abrir terminal de comandos no contêiner"
            >
              <Terminal class="w-3 h-3 text-dock-success" /> Shell
            </button>
            <button
              @click="envProject = p"
              class="px-2 py-1.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-[11px] font-mono text-dock-text-muted hover:text-dock-text flex items-center justify-center gap-1 transition-colors cursor-pointer"
              title="Variáveis de ambiente (.env) e Webhook"
            >
              <KeyRound class="w-3 h-3 text-dock-warning" /> .env
            </button>
            <button
              @click="openPreviewsModal(p)"
              class="px-2 py-1.5 rounded bg-dock-surface hover:bg-dock-bg border border-dock-border text-[11px] font-mono text-dock-text-muted hover:text-dock-text flex items-center justify-center gap-1 transition-colors cursor-pointer"
              title="Ambientes de Preview por Branch / Pull Request"
            >
              <GitBranch class="w-3 h-3 text-dock-accent" /> PRs
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
              v-if="healthchecks[p.id]?.container_state === 'running'"
              @click="stopProject(p)"
              :disabled="projectActionLoading[p.id]"
              class="px-2.5 py-1 text-xs font-mono text-dock-warning hover:bg-dock-warning/10 border border-dock-border rounded transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
              title="Interromper contêineres do projeto e suspender auto-restart"
            >
              <Square class="w-3 h-3 fill-current text-dock-warning" />
              {{ projectActionLoading[p.id] ? 'Parando...' : 'Parar' }}
            </button>
            <button
              v-else
              @click="startProject(p)"
              :disabled="projectActionLoading[p.id]"
              class="px-2.5 py-1 text-xs font-mono text-dock-success hover:bg-dock-success/10 border border-dock-border rounded transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
              title="Iniciar contêineres do projeto"
            >
              <Play class="w-3 h-3 fill-current text-dock-success" />
              {{ projectActionLoading[p.id] ? 'Iniciando...' : 'Iniciar' }}
            </button>
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

    <!-- Modal de Ambientes de Preview (Branch / Pull Request) -->
    <div
      v-if="previewProject"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in"
    >
      <div class="glass-panel w-full max-w-xl bg-dock-bg/95 border border-dock-border-light shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[88vh]">
        <div class="flex items-center justify-between px-6 py-4 border-b border-dock-border bg-dock-surface/40">
          <div class="flex items-center gap-2.5">
            <div class="p-2 rounded-lg bg-dock-accent/15 text-dock-accent">
              <GitBranch class="w-5 h-5" />
            </div>
            <div>
              <h3 class="text-base font-bold text-dock-text">
                Preview Deployments (Branch / Pull Request)
              </h3>
              <p class="text-xs text-dock-text-dim">
                {{ previewProject.name }} • Subdomínios efêmeros automáticos via Traefik
              </p>
            </div>
          </div>
          <button
            @click="previewProject = null"
            class="p-1.5 text-dock-text-muted hover:text-dock-text rounded-lg hover:bg-dock-surface transition-colors cursor-pointer"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="p-6 space-y-4 overflow-y-auto flex-1">
          <div class="p-3.5 rounded-xl bg-dock-surface/40 border border-dock-border space-y-2.5 text-xs">
            <label class="block font-medium text-dock-text">
              Lançar Novo Ambiente de Preview (Branch ou PR)
            </label>
            <div class="flex gap-2">
              <input
                v-model="newPreviewBranch"
                type="text"
                placeholder="Ex: pr-12, feat-checkout, staging"
                class="flex-1 bg-dock-bg border border-dock-border focus:border-dock-accent rounded-lg px-3 py-2 font-mono text-dock-text outline-none"
                @keyup.enter="handleCreatePreview"
              />
              <button
                @click="handleCreatePreview"
                :disabled="creatingPreview || !newPreviewBranch.trim()"
                class="px-4 py-2 rounded-lg bg-dock-accent hover:bg-dock-accent-hover text-white font-medium flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <Rocket class="w-3.5 h-3.5" />
                {{ creatingPreview ? 'Subindo Preview...' : 'Criar Preview' }}
              </button>
            </div>
            <p class="text-[11px] text-dock-text-dim">
              Cria um contêiner isolado com URL própria (<code class="text-dock-accent">&lt;branch&gt;-{{ previewProject.subdomain }}.localhost</code>) sem afetar a produção.
            </p>
          </div>

          <div class="space-y-2">
            <div class="text-xs font-mono uppercase tracking-wider text-dock-text-muted">
              Previews Ativos ({{ previewsList.length }})
            </div>
            <div v-if="loadingPreviews" class="py-8 text-center text-xs text-dock-text-dim">
              Carregando ambientes de preview...
            </div>
            <div
              v-else-if="previewsList.length === 0"
              class="p-6 rounded-xl bg-dock-bg border border-dock-border text-center text-xs text-dock-text-dim"
            >
              Nenhum ambiente de Preview ativo para este projeto. Digite uma branch ou PR acima para subir um ambiente de testes!
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="pv in previewsList"
                :key="pv.container_id"
                class="p-3 rounded-xl bg-dock-bg border border-dock-border flex items-center justify-between gap-3 text-xs"
              >
                <div class="min-w-0 space-y-1">
                  <div class="flex items-center gap-2">
                    <span class="font-mono font-semibold text-dock-text">{{ pv.branch }}</span>
                    <StatusBadge :status="pv.status" size="sm" />
                  </div>
                  <a
                    :href="pv.public_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="font-mono text-dock-accent hover:underline flex items-center gap-1 truncate"
                  >
                    {{ pv.public_url }} <ExternalLink class="w-3 h-3 shrink-0" />
                  </a>
                </div>
                <button
                  @click="handleDeletePreview(pv.branch_slug)"
                  class="px-2.5 py-1.5 rounded bg-dock-surface hover:bg-dock-error/15 border border-dock-border text-dock-text-muted hover:text-dock-error flex items-center gap-1 cursor-pointer shrink-0"
                >
                  <Trash2 class="w-3.5 h-3.5" /> Destruir
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Escalonamento Horizontal (Réplicas + Autoscaling) & RBAC por Projeto -->
    <div
      v-if="scaleProject"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in"
    >
      <div class="glass-panel w-full max-w-xl bg-dock-bg/95 border border-dock-border-light shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[88vh]">
        <div class="flex items-center justify-between px-6 py-4 border-b border-dock-border bg-dock-surface/40">
          <div class="flex items-center gap-2.5">
            <div class="p-2 rounded-lg bg-dock-accent/15 text-dock-accent">
              <Layers class="w-5 h-5" />
            </div>
            <div>
              <h3 class="text-base font-bold text-dock-text">
                Escalonamento Horizontal & RBAC Granular
              </h3>
              <p class="text-xs text-dock-text-dim">
                {{ scaleProject.name }} • Réplicas com Load Balancing Traefik e Controle de Membros
              </p>
            </div>
          </div>
          <button
            @click="scaleProject = null"
            class="p-1.5 text-dock-text-muted hover:text-dock-text rounded-lg hover:bg-dock-surface transition-colors cursor-pointer"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="p-6 space-y-5 overflow-y-auto flex-1 text-xs">
          <!-- Seção 1: Réplicas & Autoscaling -->
          <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-3">
            <div class="font-semibold text-dock-text flex items-center gap-2">
              <Layers class="w-4 h-4 text-dock-accent" />
              Réplicas Multi-Contêiner & Autoscaling por CPU
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div>
                <label class="block text-dock-text-muted mb-1">Réplicas Ativas</label>
                <input
                  v-model.number="scaleForm.replicas"
                  type="number"
                  min="1"
                  max="10"
                  class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text"
                />
              </div>
              <div>
                <label class="block text-dock-text-muted mb-1">Mín. Réplicas</label>
                <input
                  v-model.number="scaleForm.autoscale_min_replicas"
                  type="number"
                  min="1"
                  max="10"
                  class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text"
                />
              </div>
              <div>
                <label class="block text-dock-text-muted mb-1">Máx. Réplicas</label>
                <input
                  v-model.number="scaleForm.autoscale_max_replicas"
                  type="number"
                  min="1"
                  max="10"
                  class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text"
                />
              </div>
              <div>
                <label class="block text-dock-text-muted mb-1">Alvo CPU (%)</label>
                <input
                  v-model.number="scaleForm.autoscale_cpu_target"
                  type="number"
                  min="20"
                  max="95"
                  class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text"
                />
              </div>
            </div>
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1">
              <div class="space-y-1">
                <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text text-xs">
                  <input type="checkbox" v-model="scaleForm.autoscale_enabled" class="accent-dock-accent" />
                  <span>Habilitar Autoscaling Automático por Métricas de CPU</span>
                </label>
                <div>
                  <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text text-xs">
                    <input type="checkbox" v-model="scaleForm.auto_heal" class="accent-dock-accent" />
                    <span>Auto-Healing Automático (reinicia o contêiner se cair)</span>
                  </label>
                </div>
              </div>
              <button
                @click="handleSaveScale"
                :disabled="savingScale"
                class="px-4 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium cursor-pointer text-xs"
              >
                {{ savingScale ? 'Aplicando...' : 'Aplicar Escalonamento' }}
              </button>
            </div>
          </div>

          <!-- Seção 2: Controle de Acesso RBAC por Projeto -->
          <div class="p-4 rounded-xl bg-dock-surface/40 border border-dock-border space-y-3">
            <div class="font-semibold text-dock-text flex items-center gap-2">
              <Users class="w-4 h-4 text-dock-accent" />
              Membros com Permissão neste Projeto (RBAC Granular)
            </div>
            <p class="text-[11px] text-dock-text-dim">
              Quando a lista possui membros vinculados, apenas eles (e administradores globais) podem visualizar ou fazer deploy deste projeto.
            </p>
            <div class="flex flex-wrap gap-2">
              <input
                v-model="memberForm.username"
                type="text"
                placeholder="Username (ex: dev1)"
                class="flex-1 bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text"
              />
              <select
                v-model="memberForm.role"
                class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text"
              >
                <option value="developer">Developer (Deploy/Exec)</option>
                <option value="viewer">Viewer (Leitura)</option>
                <option value="admin">Admin do Projeto</option>
              </select>
              <button
                @click="handleAddProjectMember"
                class="px-3.5 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium cursor-pointer"
              >
                Vincular
              </button>
            </div>
            <div v-if="projectMembers.length === 0" class="text-[11px] text-dock-text-dim italic">
              Acesso padrão aberto à equipe global. Adicione membros acima para restringir o projeto.
            </div>
            <div v-else class="space-y-1.5">
              <div
                v-for="m in projectMembers"
                :key="m.user_id"
                class="px-3 py-1.5 rounded bg-dock-bg border border-dock-border flex items-center justify-between"
              >
                <div class="font-mono">
                  <span class="text-dock-text font-semibold">{{ m.username }}</span>
                  <span class="ml-2 px-1.5 py-0.5 rounded bg-dock-surface text-dock-accent uppercase text-[10px]">{{ m.role }}</span>
                </div>
                <button
                  @click="handleRemoveProjectMember(m.user_id)"
                  class="text-dock-text-dim hover:text-dock-error cursor-pointer"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
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

    <!-- Modal de Edição de Roteamento / URL / Quotas -->
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
