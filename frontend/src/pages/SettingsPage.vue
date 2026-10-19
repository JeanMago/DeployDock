<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import {
  HardDrive,
  Server,
  Info,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  KeyRound,
  Copy,
  Check,
  Power,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemInfo, User } from '@/services/types';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import { useAuth } from '@/composables/useAuth';

const { currentUser } = useAuth();

const sysInfo = ref<SystemInfo | null>(null);
const usersList = ref<User[]>([]);
const prodCheck = ref<{
  score: number;
  passed_count: number;
  total_count: number;
  apps_base_domain: string;
  apps_tls_enabled: boolean;
  checks: { id: string; label: string; passed: boolean; hint: string }[];
} | null>(null);
const loading = ref(true);

const isCreatingUser = ref(false);
const newUser = ref({
  username: '',
  email: '',
  password: '',
  role: 'developer' as 'admin' | 'developer' | 'viewer',
  is_active: true,
});

// Troca de senha da conta logada
const currentPass = ref('');
const newPass = ref('');
const changingPass = ref(false);

// Gerador de .env para Produção (Oracle Cloud / Hostgrid)
const envGen = ref({
  serverIp: '150.230.10.25',
  useCustomDomain: false,
  baseDomain: 'meudominio.com.br',
  panelHost: 'painel.meudominio.com.br',
  tlsEnabled: false,
  acmeEmail: 'admin@meudominio.com.br',
  adminUser: 'admin',
  adminPass: 'TroqueEstaSenhaForte#2026',
});
const copiedEnv = ref(false);

function randomHex(len = 48): string {
  const chars = 'abcdef0123456789';
  let out = '';
  for (let i = 0; i < len; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}

const generatedSecretKey = ref(randomHex(64));
const generatedDbPassword = ref(randomHex(24));
const generatedWebhookSecret = ref(randomHex(32));

const effectiveBaseDomain = computed(() => {
  if (envGen.value.useCustomDomain && envGen.value.baseDomain.trim()) {
    return envGen.value.baseDomain.trim();
  }
  const ip = envGen.value.serverIp.trim() || '150.230.10.25';
  return `${ip}.sslip.io`;
});

const effectivePanelHost = computed(() => {
  if (envGen.value.useCustomDomain && envGen.value.panelHost.trim()) {
    return envGen.value.panelHost.trim();
  }
  return `painel.${effectiveBaseDomain.value}`;
});

const generatedEnvContent = computed(() => {
  const scheme = envGen.value.tlsEnabled ? 'https' : 'http';
  return `# ==========================================================
# DeployDock — Arquivo .env de Produção (Oracle Cloud / Hostgrid)
# ==========================================================

# Banco de Dados PostgreSQL
POSTGRES_DB=deploydock
POSTGRES_USER=deploydock
POSTGRES_PASSWORD=${generatedDbPassword.value}
DATABASE_URL=postgresql+asyncpg://deploydock:${generatedDbPassword.value}@db:5432/deploydock

# Chaves Criptográficas (Fernet AES-128 + JWT + Webhooks)
SECRET_KEY=${generatedSecretKey.value}
GITHUB_WEBHOOK_SECRET=${generatedWebhookSecret.value}

# Roteamento Público das Aplicações (Traefik v3.6)
APPS_BASE_DOMAIN=${effectiveBaseDomain.value}
DEPLOYDOCK_HOST=${effectivePanelHost.value}
APPS_TLS_ENABLED=${envGen.value.tlsEnabled ? 'true' : 'false'}
ACME_EMAIL=${envGen.value.acmeEmail}
APPS_NETWORK=deploydock-apps
BACKEND_BIND_IP=127.0.0.1

# CORS Permitido
CORS_ORIGINS=["${scheme}://${effectivePanelHost.value}","http://${envGen.value.serverIp.trim()}:3000","http://localhost:3000"]

# Credenciais do Administrador Inicial
INITIAL_ADMIN_USERNAME=${envGen.value.adminUser}
INITIAL_ADMIN_EMAIL=${envGen.value.acmeEmail}
INITIAL_ADMIN_PASSWORD=${envGen.value.adminPass}
`;
});

const copyGeneratedEnv = () => {
  navigator.clipboard.writeText(generatedEnvContent.value);
  copiedEnv.value = true;
  setTimeout(() => (copiedEnv.value = false), 2000);
};

const load = async () => {
  try {
    const [info, users, prod] = await Promise.all([
      api.system.info(),
      api.auth.listUsers(),
      api.system.productionCheck().catch(() => null),
    ]);
    sysInfo.value = info;
    usersList.value = users;
    prodCheck.value = prod;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

onMounted(load);

const createUser = async () => {
  if (!newUser.value.username || !newUser.value.password || !newUser.value.email) {
    alert('Preencha username, e-mail e senha.');
    return;
  }
  isCreatingUser.value = true;
  try {
    await api.auth.createUser(newUser.value);
    newUser.value.username = '';
    newUser.value.email = '';
    newUser.value.password = '';
    await load();
  } catch (err: any) {
    alert('Erro ao criar usuário: ' + err.message);
  } finally {
    isCreatingUser.value = false;
  }
};

const handleToggleUser = async (u: User) => {
  try {
    await api.auth.toggleUser(u.id);
    await load();
  } catch (err: any) {
    alert(err?.message || 'Erro ao alterar status do usuário.');
  }
};

const handleDeleteUser = async (u: User) => {
  if (!confirm(`Deseja realmente remover o usuário "${u.username}"?`)) return;
  try {
    await api.auth.deleteUser(u.id);
    await load();
  } catch (err: any) {
    alert(err?.message || 'Erro ao remover usuário.');
  }
};

const handleChangePassword = async () => {
  if (!currentPass.value || !newPass.value) {
    alert('Preencha a senha atual e a nova senha.');
    return;
  }
  changingPass.value = true;
  try {
    await api.auth.changePassword(currentPass.value, newPass.value);
    alert('Senha alterada com sucesso!');
    currentPass.value = '';
    newPass.value = '';
    await load();
  } catch (err: any) {
    alert(err?.message || 'Erro ao alterar senha.');
  } finally {
    changingPass.value = false;
  }
};

const prune = async () => {
  if (
    !confirm(
      'Deseja realmente limpar todos os dados não utilizados do Docker (imagens soltas, contêineres e volumes parados)?'
    )
  )
    return;
  try {
    const res = await api.system.prune('all');
    const mb = (res.space_reclaimed_mb ?? (res.reclaimed_space || 0) / (1024 * 1024)).toFixed(2);
    alert(`Limpeza realizada com sucesso: ${mb} MB liberados.`);
    load();
  } catch (err) {
    alert('Erro ao executar limpeza: ' + err);
  }
};
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <h2 class="text-lg font-semibold text-dock-text">Configurações & Preparação para Produção</h2>
      <p class="text-xs text-dock-text-dim mt-0.5">
        Diagnóstico do ambiente, gerador de `.env` para VPS (Oracle Cloud / Hostgrid), controle de usuários RBAC e senhas
      </p>
    </div>

    <div v-if="loading" class="flex justify-center py-10"><LoadingSpinner /></div>
    <div v-else-if="sysInfo" class="space-y-6">
      <!-- 1. Diagnóstico de Prontidão para Produção -->
      <div v-if="prodCheck" class="glass-panel p-5 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-dock-border pb-3">
          <div>
            <h3 class="font-semibold text-sm text-dock-text">
              Checklist de Prontidão para Produção
            </h3>
            <p class="text-xs text-dock-text-dim">
              Domínio atual: <span class="font-mono text-dock-accent">{{ prodCheck.apps_base_domain }}</span> •
              HTTPS: <span class="font-mono">{{ prodCheck.apps_tls_enabled ? 'Ativo' : 'Desativado (Modo HTTP)' }}</span>
            </p>
          </div>
          <span
            class="px-2.5 py-1 rounded font-mono text-xs border self-start sm:self-auto"
            :class="
              prodCheck.score >= 80
                ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                : 'bg-dock-warning/15 text-dock-warning border-dock-warning/30'
            "
          >
            Prontidão: {{ prodCheck.passed_count }}/{{ prodCheck.total_count }} ({{ prodCheck.score }}%)
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          <div
            v-for="chk in prodCheck.checks"
            :key="chk.id"
            class="p-3 rounded bg-dock-bg border border-dock-border flex items-start gap-2.5"
          >
            <CheckCircle2 v-if="chk.passed" class="w-4 h-4 text-dock-success shrink-0 mt-0.5" />
            <AlertTriangle v-else class="w-4 h-4 text-dock-warning shrink-0 mt-0.5" />
            <div class="min-w-0">
              <div class="text-xs font-medium text-dock-text">{{ chk.label }}</div>
              <div class="text-[11px] text-dock-text-dim mt-0.5">{{ chk.hint }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Gerador Interativo de .env para Produção (Oracle Cloud / Hostgrid) -->
      <div class="glass-panel p-5 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-dock-border pb-3">
          <div>
            <h3 class="font-semibold text-sm text-dock-text">
              Gerador de `.env` para Produção (Oracle Cloud / Hostgrid)
            </h3>
            <p class="text-xs text-dock-text-dim">
              Não tem domínio comprado ainda? Informe apenas o IP público da sua VPS e usamos automaticamente `.sslip.io`!
            </p>
          </div>
          <button
            @click="copyGeneratedEnv"
            class="px-3 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white text-xs font-medium flex items-center gap-1.5 cursor-pointer self-start sm:self-auto"
          >
            <Check v-if="copiedEnv" class="w-3.5 h-3.5" />
            <Copy v-else class="w-3.5 h-3.5" />
            {{ copiedEnv ? 'Arquivo .env Copiado!' : 'Copiar .env de Produção' }}
          </button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <label class="block text-dock-text-muted mb-1">IP Público da VPS (Oracle / Hostgrid)</label>
            <input
              v-model="envGen.serverIp"
              type="text"
              placeholder="ex: 150.230.10.25"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Modo de Domínio</label>
            <select
              v-model="envGen.useCustomDomain"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            >
              <option :value="false">Sem Domínio (Usar IP.sslip.io grátis)</option>
              <option :value="true">Tenho Domínio Próprio (DNS A / *)</option>
            </select>
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">HTTPS Automático (Let's Encrypt)</label>
            <select
              v-model="envGen.tlsEnabled"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            >
              <option :value="false">HTTP (Porta 80)</option>
              <option :value="true">HTTPS Ativo (Porta 443 Let's Encrypt)</option>
            </select>
          </div>
        </div>

        <div v-if="envGen.useCustomDomain" class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div>
            <label class="block text-dock-text-muted mb-1">Seu Domínio Base (APPS_BASE_DOMAIN)</label>
            <input
              v-model="envGen.baseDomain"
              type="text"
              placeholder="ex: meudominio.com.br"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Subdomínio do Painel (DEPLOYDOCK_HOST)</label>
            <input
              v-model="envGen.panelHost"
              type="text"
              placeholder="ex: painel.meudominio.com.br"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div>
            <label class="block text-dock-text-muted mb-1">E-mail do Admin / Let's Encrypt</label>
            <input
              v-model="envGen.acmeEmail"
              type="email"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Senha Inicial do Admin</label>
            <input
              v-model="envGen.adminPass"
              type="text"
              class="w-full bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
        </div>

        <pre class="p-3 rounded bg-dock-bg border border-dock-border font-mono text-[11px] text-dock-text overflow-x-auto leading-relaxed">{{ generatedEnvContent }}</pre>
      </div>

      <!-- 3. Alterar Senha da Conta Atual -->
      <div class="glass-panel p-5 space-y-3">
        <h3 class="flex items-center gap-2 font-semibold text-sm border-b border-dock-border pb-2.5 text-dock-text">
          <KeyRound class="w-4 h-4 text-dock-accent" /> Alterar Minha Senha ({{ currentUser?.username }})
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <input
            v-model="currentPass"
            type="password"
            placeholder="Senha atual"
            class="bg-dock-bg border border-dock-border rounded px-3 py-2 font-mono text-dock-text outline-none focus:border-dock-accent"
          />
          <input
            v-model="newPass"
            type="password"
            placeholder="Nova senha (mín. 6 caracteres)"
            class="bg-dock-bg border border-dock-border rounded px-3 py-2 font-mono text-dock-text outline-none focus:border-dock-accent"
          />
          <button
            @click="handleChangePassword"
            :disabled="changingPass"
            class="bg-dock-accent hover:bg-dock-accent-hover text-white px-4 py-2 rounded font-medium transition-colors cursor-pointer disabled:opacity-50"
          >
            {{ changingPass ? 'Salvando...' : 'Atualizar Senha' }}
          </button>
        </div>
      </div>

      <!-- 4. Controle de Acesso e Usuários (RBAC) -->
      <div class="glass-panel p-5 space-y-4">
        <h3 class="flex items-center gap-2 font-semibold text-sm border-b border-dock-border pb-2.5 text-dock-text">
          <Server class="w-4 h-4 text-dock-accent" /> Controle de Acesso e Usuários (RBAC)
        </h3>

        <div class="p-3.5 rounded bg-dock-bg border border-dock-border">
          <h4 class="text-xs font-semibold text-dock-text mb-2.5">Cadastrar Novo Usuário</h4>
          <div class="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
            <input
              v-model="newUser.username"
              type="text"
              placeholder="Username (ex: dev1)"
              class="bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 text-xs text-dock-text outline-none font-mono"
            />
            <input
              v-model="newUser.email"
              type="email"
              placeholder="E-mail"
              class="bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 text-xs text-dock-text outline-none font-mono"
            />
            <input
              v-model="newUser.password"
              type="password"
              placeholder="Senha"
              class="bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 text-xs text-dock-text outline-none font-mono"
            />
            <div class="flex gap-2">
              <select
                v-model="newUser.role"
                class="bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 text-xs text-dock-text outline-none flex-1 font-mono"
              >
                <option value="developer">Developer</option>
                <option value="viewer">Viewer</option>
                <option value="admin">Admin</option>
              </select>
              <button
                @click="createUser"
                :disabled="isCreatingUser"
                class="bg-dock-accent hover:bg-dock-accent-hover text-white px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer shrink-0"
              >
                {{ isCreatingUser ? '...' : 'Criar' }}
              </button>
            </div>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-dock-border text-dock-text-muted">
                <th class="py-2 font-medium">Usuário</th>
                <th class="py-2 font-medium">E-mail</th>
                <th class="py-2 font-medium">Papel (Role)</th>
                <th class="py-2 font-medium">Status</th>
                <th class="py-2 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-dock-border">
              <tr v-for="u in usersList" :key="u.id" class="hover:bg-dock-surface/40">
                <td class="py-2.5 font-mono text-dock-text font-medium">{{ u.username }}</td>
                <td class="py-2.5 text-dock-text-dim">{{ u.email }}</td>
                <td class="py-2.5">
                  <span
                    class="font-mono text-[10px] uppercase px-2 py-0.5 rounded border"
                    :class="
                      u.role === 'admin'
                        ? 'bg-dock-accent/15 text-dock-accent border-dock-accent/30'
                        : u.role === 'developer'
                        ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                        : 'bg-dock-surface text-dock-text-dim border-dock-border'
                    "
                  >
                    {{ u.role }}
                  </span>
                </td>
                <td class="py-2.5">
                  <span
                    class="text-[11px] font-mono"
                    :class="u.is_active ? 'text-dock-success' : 'text-dock-error'"
                  >
                    {{ u.is_active ? 'Ativo' : 'Bloqueado' }}
                  </span>
                </td>
                <td class="py-2.5 text-right">
                  <div v-if="u.id !== currentUser?.id" class="inline-flex items-center gap-1.5">
                    <button
                      @click="handleToggleUser(u)"
                      class="p-1 rounded bg-dock-bg hover:bg-dock-panel border border-dock-border text-dock-text-muted hover:text-dock-text cursor-pointer"
                      :title="u.is_active ? 'Desativar usuário' : 'Ativar usuário'"
                    >
                      <Power class="w-3.5 h-3.5" />
                    </button>
                    <button
                      @click="handleDeleteUser(u)"
                      class="p-1 rounded bg-dock-bg hover:bg-dock-error/15 border border-dock-border text-dock-text-muted hover:text-dock-error cursor-pointer"
                      title="Excluir usuário"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <span v-else class="text-[10px] font-mono text-dock-text-dim">Você</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 5. Manutenção Docker -->
      <div class="glass-panel p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 class="flex items-center gap-2 font-semibold text-sm text-dock-text">
            <HardDrive class="w-4 h-4 text-dock-warning" /> Limpeza Rápida do Docker (System Prune)
          </h3>
          <p class="text-xs text-dock-text-muted mt-0.5">
            Remove contêineres parados, redes órfãs, volumes não montados e imagens antigas.
          </p>
        </div>
        <button
          @click="prune"
          class="bg-dock-surface hover:bg-dock-warning/10 text-dock-warning border border-dock-warning/30 px-3.5 py-2 rounded text-xs font-medium transition-colors flex items-center gap-2 cursor-pointer shrink-0 self-start sm:self-auto"
        >
          <Trash2 class="w-3.5 h-3.5" /> Executar Prune
        </button>
      </div>

      <div class="flex items-center justify-center text-xs text-dock-text-dim gap-2 pt-4">
        <Info class="w-4 h-4" /> DeployDock v1.0 • Plataforma GitOps & Orquestração Docker
      </div>
    </div>
  </div>
</template>
