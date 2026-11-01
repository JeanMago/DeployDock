<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import {
  ShieldCheck,
  Users,
  Github,
  Mail,
  Lock,
  Power,
  Trash2,
  RefreshCw,
  CheckCircle2,
  Plus,
  Laptop,
  LogOut,
  Search,
  Save,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import { useAuth } from '@/composables/useAuth';
import type { AdminAccessOverview, User } from '@/services/types';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const { currentUser } = useAuth();

const loading = ref(true);
const overview = ref<AdminAccessOverview | null>(null);
const savingPolicies = ref(false);
const feedbackMsg = ref('');
const errorMsg = ref('');

// Filtros da tabela de contas
const accountTypeFilter = ref<'all' | 'local' | 'github' | 'google' | 'hybrid'>('all');
const searchQuery = ref('');

// Modal/Inline de edição de vínculos Git/Google de um usuário pelo Admin
const editingUserId = ref<string | null>(null);
const editLinksForm = ref({
  github_username: '',
  google_email: '',
  account_type: 'local',
});

// Formulário para criar nova conta pré-autorizada (Local / GitHub / Google)
const creatingUser = ref(false);
const newUserForm = ref({
  username: '',
  email: '',
  password: '',
  role: 'developer' as 'admin' | 'developer' | 'viewer',
  account_type: 'local' as 'local' | 'github' | 'google' | 'hybrid',
  github_username: '',
  google_email: '',
  is_active: true,
});

const notifySuccess = (msg: string) => {
  feedbackMsg.value = msg;
  errorMsg.value = '';
  setTimeout(() => {
    if (feedbackMsg.value === msg) feedbackMsg.value = '';
  }, 4000);
};

const loadOverview = async () => {
  loading.value = true;
  try {
    overview.value = await api.auth.getAdminAccessOverview();
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao carregar painel de controle de acessos.';
  } finally {
    loading.value = false;
  }
};

onMounted(loadOverview);

const filteredAccounts = computed(() => {
  const list = overview.value?.accounts || [];
  const q = searchQuery.value.trim().toLowerCase();
  return list.filter((acc) => {
    if (accountTypeFilter.value === 'github' && !acc.github_linked) return false;
    if (accountTypeFilter.value === 'google' && !acc.google_linked) return false;
    if (accountTypeFilter.value === 'local' && acc.account_type !== 'local') return false;
    if (accountTypeFilter.value === 'hybrid' && acc.account_type !== 'hybrid') return false;
    if (!q) return true;
    return (
      acc.username.toLowerCase().includes(q) ||
      acc.email.toLowerCase().includes(q) ||
      (acc.github_username || '').toLowerCase().includes(q) ||
      (acc.google_email || '').toLowerCase().includes(q) ||
      acc.role.toLowerCase().includes(q)
    );
  });
});

const handleSavePolicies = async () => {
  if (!overview.value) return;
  savingPolicies.value = true;
  try {
    const res = await api.auth.updateAdminAccessPolicies(overview.value.policies);
    overview.value.policies = res.policies;
    notifySuccess('Políticas globais de login e tipos de contas permitidos atualizadas!');
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao salvar políticas.';
  } finally {
    savingPolicies.value = false;
  }
};

const handleCreateAccount = async () => {
  if (!newUserForm.value.username.trim() || !newUserForm.value.email.trim()) {
    errorMsg.value = 'Informe ao menos username e e-mail da conta.';
    return;
  }
  creatingUser.value = true;
  try {
    const pwd = newUserForm.value.password.trim() || 'OAuthAccount#2026';
    await api.auth.createUser({
      ...newUserForm.value,
      password: pwd,
    });
    newUserForm.value = {
      username: '',
      email: '',
      password: '',
      role: 'developer',
      account_type: 'local',
      github_username: '',
      google_email: '',
      is_active: true,
    };
    await loadOverview();
    notifySuccess('Nova conta cadastrada e configurada com sucesso!');
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao criar conta.';
  } finally {
    creatingUser.value = false;
  }
};

const handleUpdateRole = async (acc: User, role: 'admin' | 'developer' | 'viewer') => {
  try {
    await api.auth.adminUpdateUserAccess(acc.id, { role });
    await loadOverview();
    notifySuccess(`Nível de acesso de @${acc.username} atualizado para ${role.toUpperCase()}.`);
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao alterar nível de acesso.';
    await loadOverview();
  }
};

const handleToggleActive = async (acc: User) => {
  try {
    await api.auth.adminUpdateUserAccess(acc.id, { is_active: !acc.is_active });
    await loadOverview();
    notifySuccess(
      `Conta @${acc.username} ${!acc.is_active ? 'reativada' : 'bloqueada'} com sucesso.`
    );
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao alterar status da conta.';
  }
};

const handleToggleEmailNotif = async (acc: User) => {
  try {
    await api.auth.adminUpdateUserAccess(acc.id, {
      email_notifications: !acc.email_notifications,
    });
    await loadOverview();
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao atualizar notificação por e-mail.';
  }
};

const startEditLinks = (acc: User) => {
  editingUserId.value = acc.id;
  editLinksForm.value = {
    github_username: acc.github_username || '',
    google_email: acc.google_email || '',
    account_type: acc.account_type || 'local',
  };
};

const saveEditLinks = async (acc: User) => {
  try {
    await api.auth.adminUpdateUserAccess(acc.id, {
      github_username: editLinksForm.value.github_username,
      google_email: editLinksForm.value.google_email,
      account_type: editLinksForm.value.account_type,
    });
    editingUserId.value = null;
    await loadOverview();
    notifySuccess(`Tipos de conta e vínculos OAuth de @${acc.username} atualizados!`);
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao atualizar vínculos da conta.';
  }
};

const handleRevokeUserSessions = async (acc: User) => {
  try {
    const res = await api.auth.adminRevokeUserSessions(acc.id);
    await loadOverview();
    notifySuccess(`${res.revoked_sessions} sessão(ões) ativa(s) encerrada(s) para @${acc.username}.`);
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao encerrar sessões.';
  }
};

const handleRevokeSession = async (sessionId: string) => {
  try {
    await api.auth.adminRevokeSingleSession(sessionId);
    await loadOverview();
    notifySuccess('Sessão encerrada com sucesso.');
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao encerrar sessão.';
  }
};

const handleDeleteAccount = async (acc: User) => {
  if (!confirm(`Deseja realmente excluir a conta "${acc.username}"?`)) return;
  try {
    await api.auth.deleteUser(acc.id);
    await loadOverview();
    notifySuccess(`Conta @${acc.username} removida.`);
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao remover conta.';
  }
};
</script>

<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Cabeçalho -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-dock-border">
      <div>
        <h2 class="text-lg font-semibold text-dock-text flex items-center gap-2">
          <ShieldCheck class="w-5 h-5 text-dock-accent" />
          Controle de Acessos & Tipos de Contas Logadas (Admin)
        </h2>
        <p class="text-xs text-dock-text-dim mt-0.5">
          Gerencie quais tipos de contas (Local, Git/GitHub, Google) podem acessar o DeployDock, permissões RBAC e sessões logadas.
        </p>
      </div>
      <button
        @click="loadOverview"
        class="px-3 py-1.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-medium text-dock-text flex items-center gap-1.5 cursor-pointer self-start"
      >
        <RefreshCw class="w-3.5 h-3.5 text-dock-accent" /> Atualizar Acessos
      </button>
    </div>

    <!-- Alertas de Feedback -->
    <div
      v-if="feedbackMsg"
      class="px-3.5 py-2.5 rounded-lg bg-dock-success/15 border border-dock-success/30 text-dock-success text-xs flex items-center gap-2"
    >
      <CheckCircle2 class="w-4 h-4 shrink-0" />
      <span>{{ feedbackMsg }}</span>
    </div>
    <div
      v-if="errorMsg"
      class="px-3.5 py-2.5 rounded-lg bg-dock-error/15 border border-dock-error/30 text-dock-error text-xs"
    >
      {{ errorMsg }}
    </div>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner /></div>

    <div v-else-if="overview" class="space-y-6 text-xs">
      <!-- 1. KPIs de Tipos de Contas & Sessões -->
      <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div class="glass-panel p-3.5 space-y-1">
          <div class="text-dock-text-dim flex items-center justify-between">
            <span>Total de Contas</span>
            <Users class="w-3.5 h-3.5 text-dock-accent" />
          </div>
          <div class="text-xl font-mono font-bold text-dock-text">
            {{ overview.stats.total_accounts }}
          </div>
          <div class="text-[10px] font-mono text-dock-success">
            {{ overview.stats.active_accounts }} ativas • {{ overview.stats.blocked_accounts }} bloqueadas
          </div>
        </div>

        <div class="glass-panel p-3.5 space-y-1">
          <div class="text-dock-text-dim flex items-center justify-between">
            <span>Contas Git / GitHub</span>
            <Github class="w-3.5 h-3.5 text-dock-accent" />
          </div>
          <div class="text-xl font-mono font-bold text-dock-accent">
            {{ overview.stats.github_linked_count }}
          </div>
          <div class="text-[10px] font-mono text-dock-text-dim">
            OAuth / Token Git vinculado
          </div>
        </div>

        <div class="glass-panel p-3.5 space-y-1">
          <div class="text-dock-text-dim flex items-center justify-between">
            <span>Contas Google</span>
            <Mail class="w-3.5 h-3.5 text-dock-success" />
          </div>
          <div class="text-xl font-mono font-bold text-dock-success">
            {{ overview.stats.google_linked_count }}
          </div>
          <div class="text-[10px] font-mono text-dock-text-dim">
            Google SSO / Gmail vinculado
          </div>
        </div>

        <div class="glass-panel p-3.5 space-y-1">
          <div class="text-dock-text-dim flex items-center justify-between">
            <span>Contas Locais / Híbridas</span>
            <Lock class="w-3.5 h-3.5 text-dock-warning" />
          </div>
          <div class="text-xl font-mono font-bold text-dock-text">
            {{ overview.stats.local_only_count }} / {{ overview.stats.hybrid_count }}
          </div>
          <div class="text-[10px] font-mono text-dock-text-dim">
            Apenas Local / Múltiplos Provedores
          </div>
        </div>

        <div class="glass-panel p-3.5 space-y-1">
          <div class="text-dock-text-dim flex items-center justify-between">
            <span>Sessões Conectadas</span>
            <Laptop class="w-3.5 h-3.5 text-dock-accent" />
          </div>
          <div class="text-xl font-mono font-bold text-dock-text">
            {{ overview.stats.active_sessions_count }}
          </div>
          <div class="text-[10px] font-mono text-dock-text-dim">
            {{ overview.stats.admins_count }} Admin • {{ overview.stats.developers_count }} Dev
          </div>
        </div>
      </div>

      <!-- 2. Políticas Globais de Login e Tipos de Contas Permitidos -->
      <div class="glass-panel p-5 space-y-4 border border-dock-accent/30">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-dock-border pb-3">
          <div>
            <h3 class="font-semibold text-sm text-dock-text">
              Políticas de Login & Controle de Tipos de Contas Permitidos
            </h3>
            <p class="text-[11px] text-dock-text-dim mt-0.5">
              Defina quais métodos de login estão liberados, o nível de acesso padrão para contas Git/Google e domínios autorizados.
            </p>
          </div>
          <button
            @click="handleSavePolicies"
            :disabled="savingPolicies"
            class="px-3.5 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium flex items-center gap-1.5 cursor-pointer self-start"
          >
            <Save class="w-3.5 h-3.5" />
            {{ savingPolicies ? 'Salvando...' : 'Salvar Políticas de Acesso' }}
          </button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <label class="p-3 rounded bg-dock-bg border border-dock-border flex items-center gap-2.5 cursor-pointer">
            <input type="checkbox" v-model="overview.policies.allow_local_login" class="accent-dock-accent" />
            <div>
              <div class="font-medium text-dock-text">Login Conta Local</div>
              <div class="text-[10px] text-dock-text-dim">Usuário e senha internos</div>
            </div>
          </label>

          <label class="p-3 rounded bg-dock-bg border border-dock-border flex items-center gap-2.5 cursor-pointer">
            <input type="checkbox" v-model="overview.policies.allow_github_login" class="accent-dock-accent" />
            <div>
              <div class="font-medium text-dock-text">Login Conta Git (GitHub)</div>
              <div class="text-[10px] text-dock-text-dim">OAuth Device & Token Git</div>
            </div>
          </label>

          <label class="p-3 rounded bg-dock-bg border border-dock-border flex items-center gap-2.5 cursor-pointer">
            <input type="checkbox" v-model="overview.policies.allow_google_login" class="accent-dock-accent" />
            <div>
              <div class="font-medium text-dock-text">Login Conta Google</div>
              <div class="text-[10px] text-dock-text-dim">Google Workspace & Gmail</div>
            </div>
          </label>

          <label class="p-3 rounded bg-dock-bg border border-dock-border flex items-center gap-2.5 cursor-pointer">
            <input type="checkbox" v-model="overview.policies.auto_register_oauth" class="accent-dock-accent" />
            <div>
              <div class="font-medium text-dock-text">Auto-Cadastro OAuth</div>
              <div class="text-[10px] text-dock-text-dim">Criar conta no 1º login Git/Google</div>
            </div>
          </label>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div>
            <label class="block text-dock-text-muted mb-1">Papel Padrão para Contas Git/Google</label>
            <select
              v-model="overview.policies.default_oauth_role"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            >
              <option value="viewer">VIEWER (Somente Leitura)</option>
              <option value="developer">DEVELOPER (Deploys & Docker)</option>
              <option value="admin">ADMIN (Acesso Total)</option>
            </select>
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Domínios de E-mail Permitidos</label>
            <input
              v-model="overview.policies.allowed_email_domains"
              type="text"
              placeholder="* ou gmail.com, empresa.com.br"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">GitHub OAuth Client ID</label>
            <input
              v-model="overview.policies.github_oauth_client_id"
              type="text"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Google OAuth Client ID (Opcional)</label>
            <input
              v-model="overview.policies.google_oauth_client_id"
              type="text"
              placeholder="xxxx.apps.googleusercontent.com"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
        </div>
      </div>

      <!-- 3. Cadastrar Nova Conta (Com Pré-Vínculo Local / GitHub / Google) -->
      <div class="glass-panel p-5 space-y-3">
        <h3 class="font-semibold text-sm text-dock-text flex items-center gap-2">
          <Plus class="w-4 h-4 text-dock-accent" />
          Autorizar / Criar Nova Conta (Local, GitHub ou Google)
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-6 gap-2.5">
          <input
            v-model="newUserForm.username"
            type="text"
            placeholder="Username (ex: joao)"
            class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
          />
          <input
            v-model="newUserForm.email"
            type="email"
            placeholder="E-mail principal"
            class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
          />
          <input
            v-model="newUserForm.github_username"
            type="text"
            placeholder="Usuário Git (opcional)"
            class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
          />
          <input
            v-model="newUserForm.google_email"
            type="email"
            placeholder="E-mail Google (opcional)"
            class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
          />
          <input
            v-model="newUserForm.password"
            type="password"
            placeholder="Senha local"
            class="bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
          />
          <div class="flex gap-1.5">
            <select
              v-model="newUserForm.role"
              class="bg-dock-bg border border-dock-border rounded px-2 py-1.5 font-mono text-dock-text outline-none flex-1"
            >
              <option value="developer">Developer</option>
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </select>
            <button
              @click="handleCreateAccount"
              :disabled="creatingUser"
              class="px-3 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium cursor-pointer shrink-0"
            >
              Criar
            </button>
          </div>
        </div>
      </div>

      <!-- 4. Tabela Completa de Contas, Tipos de Contas e Controle de Acesso -->
      <div class="glass-panel p-5 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-dock-border pb-3">
          <div class="flex flex-wrap items-center gap-1.5">
            <button
              v-for="flt in [
                { id: 'all', label: 'Todas as Contas' },
                { id: 'github', label: 'Com Git / GitHub' },
                { id: 'google', label: 'Com Google' },
                { id: 'local', label: 'Apenas Local' },
                { id: 'hybrid', label: 'Híbridas (Múltiplos)' },
              ]"
              :key="flt.id"
              @click="accountTypeFilter = flt.id as any"
              class="px-2.5 py-1 rounded font-mono text-[11px] border cursor-pointer transition-colors"
              :class="
                accountTypeFilter === flt.id
                  ? 'bg-dock-accent text-white border-dock-accent'
                  : 'bg-dock-bg text-dock-text-muted border-dock-border hover:text-dock-text'
              "
            >
              {{ flt.label }}
            </button>
          </div>

          <div class="relative w-full sm:w-64">
            <Search class="w-3.5 h-3.5 text-dock-text-dim absolute left-2.5 top-2" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Buscar conta, @git ou e-mail..."
              class="w-full bg-dock-bg border border-dock-border rounded pl-8 pr-2.5 py-1 font-mono text-dock-text outline-none"
            />
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-dock-border text-dock-text-muted">
                <th class="py-2 pr-3 font-medium">Conta / E-mail</th>
                <th class="py-2 pr-3 font-medium">Tipo de Conta & Logins Vinculados</th>
                <th class="py-2 pr-3 font-medium">Nível de Acesso (RBAC)</th>
                <th class="py-2 pr-3 font-medium">Alerta E-mail</th>
                <th class="py-2 pr-3 font-medium">Último Login / Sessões</th>
                <th class="py-2 font-medium text-right">Controle Admin</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-dock-border">
              <tr v-for="acc in filteredAccounts" :key="acc.id" class="hover:bg-dock-surface/40">
                <td class="py-3 pr-3">
                  <div class="font-mono font-semibold text-dock-text flex items-center gap-1.5">
                    <span>@{{ acc.username }}</span>
                    <span
                      v-if="!acc.is_active"
                      class="px-1.5 py-0.5 rounded bg-dock-error/15 text-dock-error text-[9px] uppercase"
                    >
                      Bloqueada
                    </span>
                  </div>
                  <div class="text-[11px] font-mono text-dock-text-dim">{{ acc.email }}</div>
                </td>

                <!-- Coluna Tipo de Conta & Provedores Conectados -->
                <td class="py-3 pr-3">
                  <div v-if="editingUserId !== acc.id" class="flex flex-wrap items-center gap-1.5">
                    <span
                      class="px-2 py-0.5 rounded font-mono text-[10px] uppercase border"
                      :class="
                        acc.account_type === 'hybrid'
                          ? 'bg-dock-accent/15 text-dock-accent border-dock-accent/30'
                          : acc.account_type === 'github'
                            ? 'bg-dock-panel text-dock-text border-dock-border-light'
                            : acc.account_type === 'google'
                              ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                              : 'bg-dock-bg text-dock-text-muted border-dock-border'
                      "
                    >
                      {{ acc.account_type || 'local' }}
                    </span>
                    <span
                      v-if="acc.github_linked"
                      class="px-2 py-0.5 rounded bg-dock-bg border border-dock-border font-mono text-[10px] text-dock-accent flex items-center gap-1"
                    >
                      <Github class="w-3 h-3" /> @{{ acc.github_username }}
                    </span>
                    <span
                      v-if="acc.google_linked"
                      class="px-2 py-0.5 rounded bg-dock-bg border border-dock-border font-mono text-[10px] text-dock-success flex items-center gap-1"
                    >
                      <Mail class="w-3 h-3" /> {{ acc.google_email }}
                    </span>
                    <button
                      type="button"
                      @click="startEditLinks(acc)"
                      class="text-[10px] text-dock-accent hover:underline ml-1 cursor-pointer"
                    >
                      Editar Vínculos
                    </button>
                  </div>

                  <!-- Edição Inline de Vínculos Git/Google pelo Admin -->
                  <div v-else class="p-2 rounded bg-dock-bg border border-dock-accent space-y-1.5 max-w-xs">
                    <input
                      v-model="editLinksForm.github_username"
                      type="text"
                      placeholder="Usuário GitHub (vazio p/ remover)"
                      class="w-full bg-dock-surface border border-dock-border rounded px-2 py-1 font-mono text-[11px] text-dock-text"
                    />
                    <input
                      v-model="editLinksForm.google_email"
                      type="email"
                      placeholder="E-mail Google (vazio p/ remover)"
                      class="w-full bg-dock-surface border border-dock-border rounded px-2 py-1 font-mono text-[11px] text-dock-text"
                    />
                    <div class="flex gap-1.5">
                      <button
                        type="button"
                        @click="saveEditLinks(acc)"
                        class="px-2 py-1 rounded bg-dock-accent text-white font-medium text-[10px] cursor-pointer"
                      >
                        Salvar
                      </button>
                      <button
                        type="button"
                        @click="editingUserId = null"
                        class="px-2 py-1 rounded bg-dock-surface border border-dock-border text-dock-text-dim text-[10px] cursor-pointer"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                </td>

                <!-- Coluna Role RBAC -->
                <td class="py-3 pr-3">
                  <select
                    :disabled="acc.id === currentUser?.id"
                    :value="acc.role"
                    @change="handleUpdateRole(acc, ($event.target as HTMLSelectElement).value as any)"
                    class="bg-dock-bg border border-dock-border rounded px-2 py-1 font-mono text-[11px] uppercase text-dock-text outline-none cursor-pointer disabled:opacity-60"
                  >
                    <option value="admin">ADMIN</option>
                    <option value="developer">DEVELOPER</option>
                    <option value="viewer">VIEWER</option>
                  </select>
                </td>

                <!-- Coluna Notificação E-mail -->
                <td class="py-3 pr-3">
                  <button
                    type="button"
                    @click="handleToggleEmailNotif(acc)"
                    class="px-2 py-0.5 rounded font-mono text-[10px] border cursor-pointer"
                    :class="
                      acc.email_notifications
                        ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                        : 'bg-dock-bg text-dock-text-dim border-dock-border'
                    "
                  >
                    {{ acc.email_notifications ? 'E-mail Ativo' : 'Silenciado' }}
                  </button>
                </td>

                <!-- Coluna Último Acesso / Sessões -->
                <td class="py-3 pr-3 font-mono text-[11px]">
                  <div class="text-dock-text">
                    Via: <strong class="uppercase text-dock-accent">{{ acc.last_login_provider || 'local' }}</strong>
                    • {{ acc.active_sessions_count || 0 }} sessão(ões)
                  </div>
                  <div class="text-[10px] text-dock-text-dim">
                    {{ acc.last_login_ip ? `IP ${acc.last_login_ip}` : 'Sem login recente' }}
                  </div>
                </td>

                <!-- Coluna Ações Admin -->
                <td class="py-3 text-right">
                  <div class="inline-flex items-center gap-1.5">
                    <button
                      type="button"
                      @click="handleRevokeUserSessions(acc)"
                      class="px-2 py-1 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-dock-text-muted hover:text-dock-warning font-mono text-[10px] cursor-pointer"
                      title="Desconectar todas as sessões desta conta"
                    >
                      Deslogar
                    </button>
                    <button
                      v-if="acc.id !== currentUser?.id"
                      type="button"
                      @click="handleToggleActive(acc)"
                      class="p-1.5 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-dock-text-muted hover:text-dock-text cursor-pointer"
                      :title="acc.is_active ? 'Suspender acesso da conta' : 'Reativar acesso da conta'"
                    >
                      <Power class="w-3.5 h-3.5" />
                    </button>
                    <button
                      v-if="acc.id !== currentUser?.id"
                      type="button"
                      @click="handleDeleteAccount(acc)"
                      class="p-1.5 rounded bg-dock-bg hover:bg-dock-error/15 border border-dock-border text-dock-text-muted hover:text-dock-error cursor-pointer"
                      title="Excluir conta"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 5. Monitor de Sessões e Tipos de Contas Logadas em Tempo Real -->
      <div class="glass-panel p-5 space-y-3">
        <h3 class="font-semibold text-sm text-dock-text flex items-center gap-2 border-b border-dock-border pb-2.5">
          <Laptop class="w-4 h-4 text-dock-accent" />
          Histórico & Sessões de Contas Logadas ({{ overview.sessions.length }})
        </h3>
        <div v-if="overview.sessions.length === 0" class="py-6 text-center text-dock-text-dim">
          Nenhuma sessão autenticada registrada ainda.
        </div>
        <div v-else class="max-h-64 overflow-y-auto space-y-2 pr-1">
          <div
            v-for="sess in overview.sessions"
            :key="sess.session_id"
            class="p-3 rounded bg-dock-bg border border-dock-border flex flex-wrap items-center justify-between gap-2"
          >
            <div class="flex flex-wrap items-center gap-2.5 font-mono">
              <span class="font-semibold text-dock-text">@{{ sess.username }}</span>
              <span class="text-dock-text-dim">({{ sess.email }})</span>
              <span
                class="px-2 py-0.5 rounded text-[10px] uppercase border"
                :class="
                  sess.provider === 'github'
                    ? 'bg-dock-accent/15 text-dock-accent border-dock-accent/30'
                    : sess.provider === 'google'
                      ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                      : 'bg-dock-surface text-dock-text-muted border-dock-border'
                "
              >
                Login via {{ sess.provider }}
              </span>
              <span class="px-2 py-0.5 rounded bg-dock-surface border border-dock-border text-[10px] uppercase text-dock-text">
                {{ sess.role }}
              </span>
              <span class="text-[11px] text-dock-text-dim">IP: {{ sess.ip }}</span>
            </div>

            <div class="flex items-center gap-2">
              <span class="text-[10px] font-mono text-dock-text-dim">{{ sess.logged_in_at }}</span>
              <span
                class="px-2 py-0.5 rounded font-mono text-[10px]"
                :class="
                  sess.active
                    ? 'bg-dock-success/15 text-dock-success'
                    : 'bg-dock-surface text-dock-text-dim'
                "
              >
                {{ sess.active ? 'Conectada' : 'Revogada' }}
              </span>
              <button
                v-if="sess.active"
                type="button"
                @click="handleRevokeSession(sess.session_id)"
                class="p-1 rounded bg-dock-error/15 hover:bg-dock-error/25 border border-dock-error/30 text-dock-error cursor-pointer"
                title="Revogar esta sessão"
              >
                <LogOut class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
