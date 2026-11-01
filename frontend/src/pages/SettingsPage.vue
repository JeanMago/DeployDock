<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import {
  HardDrive,
  Info,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  KeyRound,
  Copy,
  Check,
  Power,
  Bell,
  Send,
  Shield,
  Mail,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import type { SystemInfo, User, NotificationOverview } from '@/services/types';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import { useAuth } from '@/composables/useAuth';

const { currentUser, isAdmin } = useAuth();

const sysInfo = ref<SystemInfo | null>(null);
const usersList = ref<User[]>([]);
const notifOverview = ref<NotificationOverview | null>(null);
const savingNotif = ref(false);
const testingNotif = ref(false);
const notifFeedback = ref('');

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

// Autenticação em Duas Etapas (2FA / TOTP RFC 6238)
const totpSetupData = ref<{ secret: string; otpauth_uri: string } | null>(null);
const totpOtpCode = ref('');
const totpDisablePass = ref('');
const loadingTotp = ref(false);

const handleSetup2FA = async () => {
  loadingTotp.value = true;
  try {
    totpSetupData.value = await api.auth.setup2FA();
  } catch (e: any) {
    alert(e?.message || 'Erro ao gerar segredo 2FA.');
  } finally {
    loadingTotp.value = false;
  }
};

const handleEnable2FA = async () => {
  if (!totpOtpCode.value.trim()) {
    alert('Digite o código de 6 dígitos do aplicativo autenticador.');
    return;
  }
  loadingTotp.value = true;
  try {
    await api.auth.enable2FA(totpOtpCode.value.trim());
    totpSetupData.value = null;
    totpOtpCode.value = '';
    if (currentUser.value) currentUser.value.totp_enabled = true;
    await load();
    alert('Autenticação em Duas Etapas (2FA/TOTP) ativada com sucesso!');
  } catch (e: any) {
    alert(e?.message || 'Código TOTP inválido.');
  } finally {
    loadingTotp.value = false;
  }
};

const handleDisable2FA = async () => {
  if (!totpDisablePass.value) {
    alert('Informe sua senha atual para desativar o 2FA.');
    return;
  }
  loadingTotp.value = true;
  try {
    await api.auth.disable2FA(totpDisablePass.value);
    totpDisablePass.value = '';
    if (currentUser.value) currentUser.value.totp_enabled = false;
    await load();
    alert('2FA desativado.');
  } catch (e: any) {
    alert(e?.message || 'Erro ao desativar 2FA.');
  } finally {
    loadingTotp.value = false;
  }
};

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

# Roteamento Público das Aplicações (Traefik)
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
    const [info, users, prod, notifs] = await Promise.all([
      api.system.info(),
      api.auth.listUsers().catch(() => []),
      api.system.productionCheck().catch(() => null),
      api.system.notifications().catch(() => null),
    ]);
    sysInfo.value = info;
    usersList.value = users;
    prodCheck.value = prod;
    notifOverview.value = notifs;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

onMounted(load);

const saveNotificationsConfig = async () => {
  if (!notifOverview.value) return;
  savingNotif.value = true;
  notifFeedback.value = '';
  try {
    const res = await api.system.updateNotificationsConfig(notifOverview.value.config);
    notifOverview.value = res.overview;
    notifFeedback.value = 'Canais e regras de alertas salvos com sucesso!';
    setTimeout(() => (notifFeedback.value = ''), 4000);
  } catch (e: any) {
    alert(e?.message || 'Erro ao salvar configurações de notificação.');
  } finally {
    savingNotif.value = false;
  }
};

const handleTestNotification = async () => {
  testingNotif.value = true;
  notifFeedback.value = '';
  try {
    const entry = await api.system.testNotification({
      title: 'Teste de Alerta DeployDock',
      message: 'Todos os canais de monitoramento de Deploy, WAF e Uptime estão operacionais!',
      severity: 'info',
    });
    notifFeedback.value = `Alerta de teste disparado! Canais atingidos: ${entry.channels.join(', ')}`;
    notifOverview.value = await api.system.notifications();
  } catch (e: any) {
    alert(e?.message || 'Erro ao disparar alerta de teste.');
  } finally {
    testingNotif.value = false;
  }
};

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

const handleRoleChange = async (u: User, newRole: 'admin' | 'developer' | 'viewer') => {
  try {
    await api.auth.updateUserRole(u.id, newRole);
    await load();
  } catch (err: any) {
    alert(err?.message || 'Erro ao atualizar permissão do usuário.');
    await load();
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
      <h2 class="text-lg font-semibold text-dock-text">Configurações, Alertas & Preparação para Produção</h2>
      <p class="text-xs text-dock-text-dim mt-0.5">
        Notificações Multicanal (Discord/Telegram/Slack), gerador de `.env` para VPS, checklist de produção e controle RBAC
      </p>
    </div>

    <div v-if="loading" class="flex justify-center py-10"><LoadingSpinner /></div>
    <div v-else-if="sysInfo" class="space-y-6">
      <!-- 1. Central de Alertas, Mensagens & Notificações (E-mail / Discord / Telegram / Slack / Webhook) -->
      <div v-if="notifOverview" class="glass-panel p-5 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-dock-border pb-3">
          <div>
            <h3 class="font-semibold text-sm text-dock-text flex items-center gap-2">
              <Bell class="w-4 h-4 text-dock-accent" />
              Central de Mensagens & Notificações (E-mail / Discord / Telegram / Slack / Webhook)
            </h3>
            <p class="text-xs text-dock-text-dim mt-0.5">
              Receba avisos automáticos por E-mail e Webhooks quando um deploy terminar, um ataque WAF for bloqueado ou um contêiner cair.
            </p>
          </div>
          <div class="flex items-center gap-2 self-start sm:self-auto">
            <button
              @click="handleTestNotification"
              :disabled="testingNotif"
              class="px-3 py-1.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-medium text-dock-text flex items-center gap-1.5 cursor-pointer"
            >
              <Send class="w-3.5 h-3.5 text-dock-accent" />
              {{ testingNotif ? 'Enviando...' : 'Disparar Alerta de Teste' }}
            </button>
            <button
              v-if="isAdmin"
              @click="saveNotificationsConfig"
              :disabled="savingNotif"
              class="px-3.5 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white text-xs font-medium cursor-pointer"
            >
              {{ savingNotif ? 'Salvando...' : 'Salvar Canais' }}
            </button>
          </div>
        </div>

        <div
          v-if="notifFeedback"
          class="px-3 py-2 rounded bg-dock-success/15 border border-dock-success/30 text-dock-success text-xs flex items-center gap-2"
        >
          <CheckCircle2 class="w-4 h-4 shrink-0" />
          <span>{{ notifFeedback }}</span>
        </div>

        <!-- Canal de Notificação por E-mail (SMTP & Contas Logadas) -->
        <div class="p-3.5 rounded-lg bg-dock-bg border border-dock-accent/30 space-y-3 text-xs">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="font-semibold text-dock-text flex items-center gap-2">
              <Mail class="w-4 h-4 text-dock-accent" />
              Notificação por E-mail (SMTP & Contas Logadas Git / Google / Local)
            </div>
            <div class="flex flex-wrap items-center gap-4">
              <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text font-medium">
                <input
                  type="checkbox"
                  v-model="notifOverview.config.email_enabled"
                  :disabled="!isAdmin"
                  class="accent-dock-accent"
                />
                <span>Ativar Envio por E-mail</span>
              </label>
              <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text-muted">
                <input
                  type="checkbox"
                  v-model="notifOverview.config.notify_logged_users_emails"
                  :disabled="!isAdmin"
                  class="accent-dock-accent"
                />
                <span>Notificar e-mails das contas logadas automaticamente</span>
              </label>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <div class="sm:col-span-2">
              <label class="block text-dock-text-muted mb-1">Destinatários de E-mail (separados por vírgula)</label>
              <input
                v-model="notifOverview.config.email_recipients"
                type="text"
                :disabled="!isAdmin"
                placeholder="admin@seudominio.com, equipe@gmail.com"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Remetente (From E-mail)</label>
              <input
                v-model="notifOverview.config.smtp_from_email"
                type="text"
                :disabled="!isAdmin"
                placeholder="alertas@deploydock.local"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
            <div>
              <label class="block text-dock-text-muted mb-1">Servidor SMTP (Host)</label>
              <input
                v-model="notifOverview.config.smtp_host"
                type="text"
                :disabled="!isAdmin"
                placeholder="smtp.gmail.com"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Porta SMTP</label>
              <input
                v-model.number="notifOverview.config.smtp_port"
                type="number"
                :disabled="!isAdmin"
                placeholder="587"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Usuário SMTP (Opcional)</label>
              <input
                v-model="notifOverview.config.smtp_user"
                type="text"
                :disabled="!isAdmin"
                placeholder="seuemail@gmail.com"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Senha / App Password SMTP</label>
              <input
                v-model="notifOverview.config.smtp_password"
                type="password"
                :disabled="!isAdmin"
                placeholder="••••••••••••"
                class="w-full bg-dock-surface border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
          </div>

          <div
            v-if="notifOverview.resolved_email_recipients && notifOverview.resolved_email_recipients.length > 0"
            class="text-[11px] font-mono text-dock-text-dim"
          >
            E-mails ativos na rota de disparo: <span class="text-dock-accent">{{ notifOverview.resolved_email_recipients.join(', ') }}</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div>
            <label class="block text-dock-text-muted mb-1">Discord Webhook URL</label>
            <input
              v-model="notifOverview.config.discord_webhook_url"
              type="text"
              :disabled="!isAdmin"
              placeholder="https://discord.com/api/webhooks/..."
              class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Slack Incoming Webhook URL</label>
            <input
              v-model="notifOverview.config.slack_webhook_url"
              type="text"
              :disabled="!isAdmin"
              placeholder="https://hooks.slack.com/services/..."
              class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">Telegram Bot Token</label>
            <input
              v-model="notifOverview.config.telegram_bot_token"
              type="password"
              :disabled="!isAdmin"
              placeholder="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
              class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-dock-text-muted mb-1">Telegram Chat ID</label>
              <input
                v-model="notifOverview.config.telegram_chat_id"
                type="text"
                :disabled="!isAdmin"
                placeholder="-100123456789"
                class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
            <div>
              <label class="block text-dock-text-muted mb-1">Webhook Customizado (POST)</label>
              <input
                v-model="notifOverview.config.custom_webhook_url"
                type="text"
                :disabled="!isAdmin"
                placeholder="https://seu-endpoint.com/hook"
                class="w-full bg-dock-bg border border-dock-border focus:border-dock-accent rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
          </div>
        </div>

        <!-- Gatilhos de Eventos -->
        <div class="p-3 rounded bg-dock-bg border border-dock-border flex flex-wrap items-center justify-between gap-3 text-xs">
          <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text">
            <input type="checkbox" v-model="notifOverview.config.notify_on_deploy_success" :disabled="!isAdmin" class="accent-dock-accent" />
            <span>Deploy com Sucesso</span>
          </label>
          <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text">
            <input type="checkbox" v-model="notifOverview.config.notify_on_deploy_failure" :disabled="!isAdmin" class="accent-dock-accent" />
            <span>Falha / Rollback de Deploy</span>
          </label>
          <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text">
            <input type="checkbox" v-model="notifOverview.config.notify_on_waf_block" :disabled="!isAdmin" class="accent-dock-accent" />
            <span>Ataque Bloqueado pelo WAF</span>
          </label>
          <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text">
            <input type="checkbox" v-model="notifOverview.config.notify_on_container_down" :disabled="!isAdmin" class="accent-dock-accent" />
            <span>Queda de Contêiner / Auto-Heal</span>
          </label>
          <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text">
            <input type="checkbox" v-model="notifOverview.config.notify_on_high_resource" :disabled="!isAdmin" class="accent-dock-accent" />
            <span>CPU/RAM &gt; {{ notifOverview.config.cpu_threshold_percent }}%</span>
          </label>
        </div>

        <!-- Últimos Alertas Disparados -->
        <div v-if="notifOverview.history.length > 0" class="space-y-1.5 pt-1">
          <div class="text-[11px] font-mono uppercase text-dock-text-dim">
            Últimos Alertas Disparados ({{ notifOverview.history.length }})
          </div>
          <div class="max-h-36 overflow-y-auto space-y-1.5 font-mono text-xs">
            <div
              v-for="item in notifOverview.history.slice(0, 6)"
              :key="item.id"
              class="px-3 py-2 rounded bg-dock-bg border border-dock-border flex items-center justify-between gap-2"
            >
              <div class="min-w-0">
                <span class="font-semibold text-dock-text">{{ item.title }}</span>
                <span class="text-dock-text-dim ml-2 truncate">{{ item.message }}</span>
              </div>
              <span class="px-2 py-0.5 rounded bg-dock-surface border border-dock-border text-[10px] text-dock-accent shrink-0">
                {{ item.channels.join(', ') }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Diagnóstico de Prontidão para Produção -->
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

      <!-- 3. Gerador Interativo de .env para Produção (Oracle Cloud / Hostgrid) -->
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

      <!-- 4. Alterar Senha da Conta Atual + Autenticação em Duas Etapas (2FA / TOTP) -->
      <div class="glass-panel p-5 space-y-4">
        <h3 class="flex items-center gap-2 font-semibold text-sm border-b border-dock-border pb-2.5 text-dock-text">
          <KeyRound class="w-4 h-4 text-dock-accent" /> Segurança da Minha Conta ({{ currentUser?.username }}) • Senha & 2FA (TOTP)
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

        <!-- Seção 2FA / TOTP (RFC 6238) -->
        <div class="p-3.5 rounded bg-dock-bg border border-dock-border space-y-3 text-xs">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div class="font-semibold text-dock-text flex items-center gap-2">
                <Shield class="w-4 h-4 text-dock-accent" />
                Autenticação em Duas Etapas (2FA / TOTP — Google Authenticator, Authy, 1Password)
              </div>
              <div class="text-dock-text-dim mt-0.5">
                Protege o login com código temporário de 6 dígitos (RFC 6238).
              </div>
            </div>
            <span
              class="px-2.5 py-1 rounded font-mono text-[11px] border self-start sm:self-auto"
              :class="
                currentUser?.totp_enabled
                  ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                  : 'bg-dock-surface text-dock-text-muted border-dock-border'
              "
            >
              {{ currentUser?.totp_enabled ? '2FA ATIVO' : '2FA DESATIVADO' }}
            </span>
          </div>

          <div v-if="!currentUser?.totp_enabled" class="space-y-3">
            <button
              v-if="!totpSetupData"
              @click="handleSetup2FA"
              :disabled="loadingTotp"
              class="px-3.5 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium cursor-pointer"
            >
              {{ loadingTotp ? 'Gerando...' : 'Configurar 2FA Agora' }}
            </button>

            <div v-else class="p-3 rounded bg-dock-surface border border-dock-border space-y-2.5">
              <div class="text-dock-text">
                1. Adicione a chave secreta Base32 abaixo no seu app autenticador (ou copie a URI TOTP):
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-[11px]">
                <div class="p-2 rounded bg-dock-bg border border-dock-border text-dock-accent break-all">
                  Segredo: {{ totpSetupData.secret }}
                </div>
                <div class="p-2 rounded bg-dock-bg border border-dock-border text-dock-text-dim break-all">
                  {{ totpSetupData.otpauth_uri }}
                </div>
              </div>
              <div class="flex flex-wrap items-center gap-2 pt-1">
                <input
                  v-model="totpOtpCode"
                  type="text"
                  maxlength="8"
                  placeholder="Código de 6 dígitos (ex: 123456)"
                  class="bg-dock-bg border border-dock-border rounded px-3 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
                />
                <button
                  @click="handleEnable2FA"
                  :disabled="loadingTotp"
                  class="px-3.5 py-1.5 rounded bg-dock-success/20 hover:bg-dock-success/30 border border-dock-success/40 text-dock-success font-medium cursor-pointer"
                >
                  Confirmar e Ativar 2FA
                </button>
              </div>
            </div>
          </div>

          <div v-else class="flex flex-wrap items-center gap-2">
            <input
              v-model="totpDisablePass"
              type="password"
              placeholder="Confirme sua senha atual para desativar o 2FA"
              class="flex-1 min-w-[240px] bg-dock-surface border border-dock-border rounded px-3 py-1.5 font-mono text-dock-text outline-none"
            />
            <button
              @click="handleDisable2FA"
              :disabled="loadingTotp"
              class="px-3.5 py-1.5 rounded bg-dock-error/15 hover:bg-dock-error/25 border border-dock-error/30 text-dock-error font-medium cursor-pointer"
            >
              Desativar 2FA
            </button>
          </div>
        </div>
      </div>

      <!-- 5. Controle de Acesso e Usuários (RBAC) -->
      <div class="glass-panel p-5 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-dock-border pb-2.5">
          <h3 class="flex items-center gap-2 font-semibold text-sm text-dock-text">
            <Shield class="w-4 h-4 text-dock-accent" /> Controle de Acesso Baseado em Papéis (RBAC)
          </h3>
          <span class="text-[11px] font-mono text-dock-text-dim">
            Seu nível atual: <strong class="text-dock-accent uppercase">{{ currentUser?.role }}</strong>
          </span>
        </div>

        <!-- Matriz rápida de permissões RBAC -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          <div class="p-2.5 rounded bg-dock-bg border border-dock-border">
            <div class="font-mono font-semibold text-dock-accent uppercase text-[11px]">Admin</div>
            <div class="text-dock-text-dim mt-0.5">Acesso total: projetos, contêineres, WAF, usuários RBAC, notificações e prune.</div>
          </div>
          <div class="p-2.5 rounded bg-dock-bg border border-dock-border">
            <div class="font-mono font-semibold text-dock-success uppercase text-[11px]">Developer</div>
            <div class="text-dock-text-dim mt-0.5">Deploys, rollbacks, preview branches, editor de arquivos, terminal exec e backups.</div>
          </div>
          <div class="p-2.5 rounded bg-dock-bg border border-dock-border">
            <div class="font-mono font-semibold text-dock-text-muted uppercase text-[11px]">Viewer (Auditor)</div>
            <div class="text-dock-text-dim mt-0.5">Somente leitura: monitora métricas, logs, status de projetos e painel de segurança.</div>
          </div>
        </div>

        <div v-if="isAdmin" class="p-3.5 rounded bg-dock-bg border border-dock-border">
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
                <th class="py-2 font-medium">Papel (Role RBAC)</th>
                <th class="py-2 font-medium">Status</th>
                <th class="py-2 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-dock-border">
              <tr v-for="u in usersList" :key="u.id" class="hover:bg-dock-surface/40">
                <td class="py-2.5 font-mono text-dock-text font-medium">{{ u.username }}</td>
                <td class="py-2.5 text-dock-text-dim">{{ u.email }}</td>
                <td class="py-2.5">
                  <select
                    v-if="isAdmin && u.id !== currentUser?.id"
                    :value="u.role"
                    @change="handleRoleChange(u, ($event.target as HTMLSelectElement).value as any)"
                    class="bg-dock-bg border border-dock-border rounded px-2 py-0.5 font-mono text-[11px] uppercase text-dock-text outline-none cursor-pointer"
                  >
                    <option value="admin">ADMIN</option>
                    <option value="developer">DEVELOPER</option>
                    <option value="viewer">VIEWER</option>
                  </select>
                  <span
                    v-else
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
                  <div v-if="isAdmin && u.id !== currentUser?.id" class="inline-flex items-center gap-1.5">
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
                  <span v-else-if="u.id === currentUser?.id" class="text-[10px] font-mono text-dock-text-dim">Você</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 6. Manutenção Docker -->
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
