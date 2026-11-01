<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import {
  User as UserIcon,
  Github,
  Mail,
  Shield,
  KeyRound,
  CheckCircle2,
  Copy,
  ExternalLink,
  RefreshCw,
  Bell,
  Send,
  Trash2,
  LogIn,
  Laptop,
} from 'lucide-vue-next';
import { api } from '@/services/api';
import { useAuth } from '@/composables/useAuth';
import type { User, LoggedSessionItem, GitHubIntegrationStatus } from '@/services/types';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const { currentUser, loginWithGithub, loginWithGoogle, setSession } = useAuth();

const loading = ref(true);
const feedbackMsg = ref('');
const errorMsg = ref('');

const accountUser = ref<User | null>(null);
const accountMeta = ref<Record<string, any>>({});
const accountSessions = ref<LoggedSessionItem[]>([]);
const githubPaas = ref<GitHubIntegrationStatus | null>(null);

// Formulário de Perfil e Notificações por E-mail
const profileForm = ref({
  full_name: '',
  email: '',
  avatar_url: '',
  email_notifications: true,
  notify_deploy_email: true,
  notify_security_email: true,
});
const savingProfile = ref(false);
const testingEmail = ref(false);

// Formulário Vínculo/Login GitHub
const ghForm = ref({
  username: '',
  token: '',
});
const ghDeviceFlow = ref<{ user_code: string; verification_uri: string; interval: number } | null>(null);
const ghDeviceStatusMsg = ref('');
let ghPollTimer: ReturnType<typeof setInterval> | null = null;

// Formulário Vínculo/Login Google
const googleForm = ref({
  email: '',
  name: '',
  picture: '',
  id_token: '',
  app_password: '',
});
const googleDeviceFlow = ref<{ user_code: string; verification_uri: string; interval: number } | null>(null);
const googleDeviceStatusMsg = ref('');
let googlePollTimer: ReturnType<typeof setInterval> | null = null;

// Senha e 2FA
const currentPass = ref('');
const newPass = ref('');
const changingPass = ref(false);
const totpSetupData = ref<{ secret: string; otpauth_uri: string } | null>(null);
const totpOtpCode = ref('');
const totpDisableCode = ref('');

const showFeedback = (msg: string) => {
  feedbackMsg.value = msg;
  errorMsg.value = '';
  setTimeout(() => {
    if (feedbackMsg.value === msg) feedbackMsg.value = '';
  }, 4500);
};

const loadAccount = async () => {
  loading.value = true;
  try {
    const data = await api.auth.getAccount();
    accountUser.value = data.user;
    accountMeta.value = data.meta || {};
    accountSessions.value = data.sessions || [];
    githubPaas.value = data.github_paas || null;

    if (currentUser.value) {
      currentUser.value = data.user;
      localStorage.setItem('deploydock_user', JSON.stringify(data.user));
    }

    profileForm.value = {
      full_name: data.user.full_name || data.user.username,
      email: data.user.email,
      avatar_url: data.user.avatar_url || '',
      email_notifications: data.meta?.email_notifications ?? true,
      notify_deploy_email: data.meta?.notify_deploy_email ?? true,
      notify_security_email: data.meta?.notify_security_email ?? true,
    };

    ghForm.value.username =
      data.user.github_username || data.github_paas?.username || 'JeanMago';
    const existingEmail =
      data.user.google_email ||
      (!data.user.email.includes('.sslip.io') && !data.user.email.includes('.localhost')
        ? data.user.email
        : '');
    googleForm.value.email = existingEmail;
    googleForm.value.name =
      data.meta?.google_name ||
      (existingEmail ? existingEmail.split('@')[0] : data.user.full_name || data.user.username);

    if (data.github_paas && !data.github_paas.connected && data.github_paas.device_flow?.user_code) {
      ghDeviceFlow.value = data.github_paas.device_flow;
      startGithubDevicePollLoop(data.github_paas.device_flow.interval || 5);
    }
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao carregar dados da conta.';
  } finally {
    loading.value = false;
  }
};

const handleGooglePopupMessage = async (event: MessageEvent) => {
  if (!event.data || event.data.type !== 'DEPLOYDOCK_GOOGLE_OAUTH') return;
  const tok = event.data.id_token || event.data.access_token || '';
  if (!tok) return;
  googleForm.value.id_token = tok;
  await handleLinkGoogle();
};

onMounted(() => {
  loadAccount();
  window.addEventListener('message', handleGooglePopupMessage);
});

onUnmounted(() => {
  if (ghPollTimer) clearInterval(ghPollTimer);
  if (googlePollTimer) clearInterval(googlePollTimer);
  window.removeEventListener('message', handleGooglePopupMessage);
});

const handleSaveProfile = async () => {
  savingProfile.value = true;
  errorMsg.value = '';
  try {
    const res = await api.auth.updateAccountProfile(profileForm.value);
    accountUser.value = res.user;
    accountMeta.value = res.meta;
    showFeedback('Perfil e preferências de notificação por e-mail salvos com sucesso!');
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao atualizar perfil.';
  } finally {
    savingProfile.value = false;
  }
};

const handleTestEmailAlert = async () => {
  testingEmail.value = true;
  errorMsg.value = '';
  try {
    const targetEmail =
      accountUser.value?.google_email || profileForm.value.email || accountUser.value?.email;
    const entry = await api.system.testNotification({
      title: `Teste de Notificação por E-mail (${accountUser.value?.username})`,
      message: `Este é um alerta de teste enviado para o e-mail da sua conta (${targetEmail}). Seus avisos de Deploy e Segurança estão ativos!`,
      severity: 'info',
      email_to: targetEmail,
    });
    showFeedback(
      `Notificação enviada para ${targetEmail}! Canais atingidos: ${entry.channels.join(', ')}`
    );
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao disparar e-mail de teste.';
  } finally {
    testingEmail.value = false;
  }
};

// Fluxo GitHub na Tela de Conta
const startGithubDevicePollLoop = (intervalSec = 7) => {
  if (ghPollTimer) clearInterval(ghPollTimer);
  ghPollTimer = setInterval(async () => {
    try {
      const res = await api.paas.pollGithubDeviceFlow();
      if (res.status === 'connected') {
        if (ghPollTimer) clearInterval(ghPollTimer);
        ghDeviceFlow.value = null;
        ghDeviceStatusMsg.value = '';
        await api.auth.linkGithubAccount({ use_paas_connected: true });
        await loadAccount();
        showFeedback(`Conta GitHub @${res.github.username} autorizada e vinculada com sucesso!`);
      } else if (res.error_description) {
        ghDeviceStatusMsg.value = res.error_description;
      }
    } catch {
      // continua aguardando
    }
  }, Math.max(7, intervalSec + 2) * 1000);
};

const handleStartGithubDevice = async () => {
  errorMsg.value = '';
  ghDeviceStatusMsg.value = '';
  try {
    const flow = await api.paas.startGithubDeviceFlow();
    ghDeviceFlow.value = flow;
    try {
      await navigator.clipboard.writeText(flow.user_code);
    } catch {
      // ignore
    }
    startGithubDevicePollLoop(flow.interval || 5);
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao iniciar OAuth Device Flow no GitHub.';
  }
};

const copyAndOpenGithubDevice = async () => {
  if (!ghDeviceFlow.value) return;
  try {
    await navigator.clipboard.writeText(ghDeviceFlow.value.user_code);
  } catch {
    // ignore
  }
  window.open(ghDeviceFlow.value.verification_uri, '_blank', 'noopener,noreferrer');
};

const handleManualConfirmGithubDevice = async () => {
  ghDeviceStatusMsg.value = 'Verificando autorização junto ao GitHub...';
  try {
    const res = await api.paas.pollGithubDeviceFlow();
    if (res.status === 'connected') {
      if (ghPollTimer) clearInterval(ghPollTimer);
      ghDeviceFlow.value = null;
      ghDeviceStatusMsg.value = '';
      await api.auth.linkGithubAccount({ use_paas_connected: true });
      await loadAccount();
      showFeedback(`Conta GitHub @${res.github.username} vinculada com sucesso!`);
    } else {
      ghDeviceStatusMsg.value =
        res.error_description || 'Ainda aguardando autorização do código no GitHub...';
    }
  } catch (e: any) {
    ghDeviceStatusMsg.value = e?.message || 'Erro ao verificar autorização.';
  }
};

const handleLinkGithub = async (usePaas = false) => {
  errorMsg.value = '';
  try {
    await api.auth.linkGithubAccount({
      username: ghForm.value.username.trim() || undefined,
      token: ghForm.value.token.trim() || undefined,
      use_paas_connected: usePaas,
    });
    ghForm.value.token = '';
    await loadAccount();
    showFeedback('Conta Git / GitHub vinculada com sucesso!');
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao vincular conta GitHub.';
  }
};

const handleSwitchLoginGithub = async () => {
  errorMsg.value = '';
  try {
    const res = await loginWithGithub({
      username: accountUser.value?.github_username || ghForm.value.username.trim() || undefined,
      token: ghForm.value.token.trim() || undefined,
      use_paas_connected: githubPaas.value?.connected || false,
    });
    setSession(res.access_token, res.user);
    await loadAccount();
    showFeedback(`Sessão autenticada via Conta GitHub (@${res.user.github_username || res.user.username})!`);
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao autenticar sessão via GitHub.';
  }
};

const handleUnlinkGithub = async () => {
  await api.auth.unlinkGithubAccount();
  await loadAccount();
  showFeedback('Conta GitHub desvinculada.');
};

// Fluxo Google na Tela de Conta (OAuth Device Flow em google.com/device + Gmail SMTP)
const startGoogleDevicePollLoop = (intervalSec = 5) => {
  if (googlePollTimer) clearInterval(googlePollTimer);
  const pollMs = Math.max(6, intervalSec + 1) * 1000;
  googlePollTimer = setInterval(async () => {
    try {
      const res = await api.auth.pollGoogleOAuthDevice();
      if (res.status === 'connected') {
        if (googlePollTimer) clearInterval(googlePollTimer);
        googleDeviceFlow.value = null;
        if (res.access_token && res.user) {
          setSession(res.access_token, res.user);
        }
        await loadAccount();
        showFeedback(
          `Conta Google (${res.google?.email || res.user?.google_email || 'Gmail'}) conectada e vinculada com sucesso!`
        );
      } else if (res.error_description) {
        googleDeviceStatusMsg.value = res.error_description;
      }
    } catch {
      // continua aguardando
    }
  }, pollMs);
};

const handleStartGoogleDevice = async () => {
  errorMsg.value = '';
  googleDeviceStatusMsg.value = '';
  try {
    const flow = await api.auth.startGoogleOAuthDevice();
    googleDeviceFlow.value = flow;
    try {
      await navigator.clipboard.writeText(flow.user_code);
    } catch {
      // ignore
    }
    startGoogleDevicePollLoop(flow.interval || 5);
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao iniciar autorização OAuth do Google.';
  }
};

const copyAndOpenGoogleDevice = async () => {
  if (!googleDeviceFlow.value) return;
  try {
    await navigator.clipboard.writeText(googleDeviceFlow.value.user_code);
    showFeedback(`Código ${googleDeviceFlow.value.user_code} copiado! Cole na aba do Google que foi aberta.`);
  } catch {
    // ignore
  }
  window.open(googleDeviceFlow.value.verification_uri || 'https://www.google.com/device', '_blank', 'noopener,noreferrer');
};

const handleManualPollGoogleDevice = async () => {
  googleDeviceStatusMsg.value = 'Confirmando autorização junto ao Google...';
  try {
    const res = await api.auth.pollGoogleOAuthDevice();
    if (res.status === 'connected') {
      if (googlePollTimer) clearInterval(googlePollTimer);
      googleDeviceFlow.value = null;
      if (res.access_token && res.user) {
        setSession(res.access_token, res.user);
      }
      await loadAccount();
      showFeedback(
        `Conta Google (${res.google?.email || res.user?.google_email || 'Gmail'}) autorizada com sucesso!`
      );
    } else {
      googleDeviceStatusMsg.value =
        res.error_description || 'Ainda aguardando você colar o código em google.com/device...';
    }
  } catch (e: any) {
    googleDeviceStatusMsg.value = e?.message || 'Erro ao verificar autorização Google.';
  }
};

const handleLinkGoogle = async () => {
  if (!googleForm.value.email.trim() && !googleForm.value.id_token.trim()) {
    errorMsg.value =
      'Informe o e-mail da sua conta Google ou gere o código OAuth no Passo 1.';
    return;
  }
  errorMsg.value = '';
  try {
    const res = await api.auth.linkGoogleAccount({
      email: googleForm.value.email.trim() || undefined,
      name: googleForm.value.name.trim() || undefined,
      picture: googleForm.value.picture.trim() || undefined,
      id_token: googleForm.value.id_token.trim() || undefined,
      app_password: googleForm.value.app_password.trim() || undefined,
    });
    googleForm.value.id_token = '';
    googleForm.value.app_password = '';
    await loadAccount();
    showFeedback(
      `Conta Google (${res.user.google_email || googleForm.value.email}) autenticada e vinculada com sucesso!`
    );
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao vincular conta Google.';
  }
};

const handleSwitchLoginGoogle = async () => {
  const emailToUse = accountUser.value?.google_email || googleForm.value.email.trim();
  const tokenToUse = googleForm.value.id_token.trim();
  if (!emailToUse && !tokenToUse) {
    errorMsg.value = 'Informe seu e-mail Google ou Token OAuth primeiro.';
    return;
  }
  errorMsg.value = '';
  try {
    const res = await loginWithGoogle({
      email: emailToUse || undefined,
      name: googleForm.value.name.trim() || undefined,
      id_token: tokenToUse || undefined,
      app_password: googleForm.value.app_password.trim() || undefined,
    });
    setSession(res.access_token, res.user);
    await loadAccount();
    showFeedback(
      `Sessão autenticada com sucesso via Conta Google (${res.user.google_email || res.user.email})!`
    );
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao autenticar sessão com Google.';
  }
};

const handleUnlinkGoogle = async () => {
  await api.auth.unlinkGoogleAccount();
  await loadAccount();
  showFeedback('Conta Google desvinculada.');
};

// Senha & 2FA
const handleChangePassword = async () => {
  if (!currentPass.value || !newPass.value) {
    errorMsg.value = 'Preencha a senha atual e a nova senha.';
    return;
  }
  changingPass.value = true;
  try {
    await api.auth.changePassword(currentPass.value, newPass.value);
    currentPass.value = '';
    newPass.value = '';
    showFeedback('Senha local atualizada com sucesso!');
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao alterar senha.';
  } finally {
    changingPass.value = false;
  }
};

const handleSetup2FA = async () => {
  totpSetupData.value = await api.auth.setup2FA();
};

const handleEnable2FA = async () => {
  if (!totpOtpCode.value.trim()) return;
  try {
    await api.auth.enable2FA(totpOtpCode.value.trim());
    totpSetupData.value = null;
    totpOtpCode.value = '';
    await loadAccount();
    showFeedback('Autenticação 2FA ativada com sucesso!');
  } catch (e: any) {
    errorMsg.value = e?.message || 'Código 2FA inválido.';
  }
};

const handleDisable2FA = async () => {
  try {
    await api.auth.disable2FA(totpDisableCode.value.trim());
    totpDisableCode.value = '';
    await loadAccount();
    showFeedback('Autenticação 2FA desativada.');
  } catch (e: any) {
    errorMsg.value = e?.message || 'Erro ao desativar 2FA.';
  }
};
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <!-- Cabeçalho -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-dock-border">
      <div>
        <h2 class="text-lg font-semibold text-dock-text flex items-center gap-2">
          <UserIcon class="w-5 h-5 text-dock-accent" />
          Minha Conta & Logins Conectados (Git / GitHub & Google)
        </h2>
        <p class="text-xs text-dock-text-dim mt-0.5">
          Gerencie seu perfil, conecte ou faça login com sua conta do GitHub e do Google, configure alertas por e-mail e segurança 2FA.
        </p>
      </div>
      <button
        @click="loadAccount"
        class="px-3 py-1.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-xs font-medium text-dock-text flex items-center gap-1.5 cursor-pointer self-start"
      >
        <RefreshCw class="w-3.5 h-3.5 text-dock-accent" /> Atualizar Conta
      </button>
    </div>

    <!-- Mensagens de Feedback / Erro -->
    <div
      v-if="feedbackMsg"
      class="px-3.5 py-2.5 rounded-lg bg-dock-success/15 border border-dock-success/30 text-dock-success text-xs flex items-center gap-2"
    >
      <CheckCircle2 class="w-4 h-4 shrink-0" />
      <span>{{ feedbackMsg }}</span>
    </div>
    <div
      v-if="errorMsg"
      class="px-3.5 py-2.5 rounded-lg bg-dock-error/15 border border-dock-error/30 text-dock-error text-xs flex items-center gap-2"
    >
      <span>{{ errorMsg }}</span>
    </div>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner /></div>

    <div v-else-if="accountUser" class="space-y-6 text-xs">
      <!-- 1. Resumo da Conta Logada -->
      <div class="glass-panel p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border border-dock-accent/30">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 rounded-xl bg-dock-panel border border-dock-border-light flex items-center justify-center overflow-hidden text-lg font-mono font-bold text-dock-accent shrink-0">
            <img
              v-if="accountUser.avatar_url"
              :src="accountUser.avatar_url"
              alt="Avatar"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ accountUser.username.slice(0, 2).toUpperCase() }}</span>
          </div>
          <div class="space-y-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-base font-semibold text-dock-text">
                {{ accountUser.full_name || accountUser.username }}
              </span>
              <span class="font-mono text-dock-text-dim">@{{ accountUser.username }}</span>
              <span
                class="px-2 py-0.5 rounded font-mono text-[10px] uppercase border"
                :class="
                  accountUser.role === 'admin'
                    ? 'bg-dock-accent/15 text-dock-accent border-dock-accent/30'
                    : accountUser.role === 'developer'
                      ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                      : 'bg-dock-surface text-dock-text-muted border-dock-border'
                "
              >
                {{ accountUser.role }}
              </span>
            </div>
            <div class="text-dock-text-dim font-mono">{{ accountUser.email }}</div>
            <div class="flex flex-wrap items-center gap-1.5 pt-0.5">
              <span class="px-2 py-0.5 rounded bg-dock-bg border border-dock-border font-mono text-[10px] text-dock-text">
                Tipo de Conta: <strong class="uppercase text-dock-accent">{{ accountUser.account_type }}</strong>
              </span>
              <span
                v-if="accountUser.github_linked"
                class="px-2 py-0.5 rounded bg-dock-accent/15 border border-dock-accent/30 font-mono text-[10px] text-dock-accent"
              >
                Git: @{{ accountUser.github_username }}
              </span>
              <span
                v-if="accountUser.google_linked"
                class="px-2 py-0.5 rounded bg-dock-success/15 border border-dock-success/30 font-mono text-[10px] text-dock-success"
              >
                Google: {{ accountUser.google_email }}
              </span>
            </div>
          </div>
        </div>

        <div class="text-right font-mono text-[11px] text-dock-text-dim space-y-1">
          <div>
            Último acesso via:
            <strong class="uppercase text-dock-text">{{ accountUser.last_login_provider || 'local' }}</strong>
          </div>
          <div v-if="accountUser.last_login_ip">IP: {{ accountUser.last_login_ip }}</div>
          <div>Sessões ativas: {{ accountUser.active_sessions_count || 1 }}</div>
        </div>
      </div>

      <!-- 2. Login e Vinculação com Conta Git (GitHub) e Conta Google -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <!-- Card A: Conta Git / GitHub -->
        <div class="glass-panel p-5 space-y-4 border border-dock-border">
          <div class="flex items-center justify-between border-b border-dock-border pb-3">
            <div class="flex items-center gap-2.5">
              <div class="p-2 rounded-lg bg-dock-bg border border-dock-border text-dock-accent">
                <Github class="w-4 h-4" />
              </div>
              <div>
                <h3 class="font-semibold text-sm text-dock-text">Conta Git / GitHub</h3>
                <p class="text-[11px] text-dock-text-dim">
                  Login social + acesso automático aos repositórios e `.env.example`
                </p>
              </div>
            </div>
            <span
              class="px-2.5 py-1 rounded font-mono text-[10px] border"
              :class="
                accountUser.github_linked
                  ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                  : 'bg-dock-bg text-dock-text-dim border-dock-border'
              "
            >
              {{ accountUser.github_linked ? `Conectado (@${accountUser.github_username})` : 'Não Vinculado' }}
            </span>
          </div>

          <!-- Ações Rápidas OAuth Device Flow -->
          <div class="p-3 rounded-lg bg-dock-bg border border-dock-border space-y-2.5">
            <div class="font-medium text-dock-text">
              Opção 1 — Autorizar no Navegador (OAuth Device Code)
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                @click="handleStartGithubDevice"
                class="px-3 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium flex items-center gap-1.5 cursor-pointer"
              >
                <Github class="w-3.5 h-3.5" />
                1. Gerar Código de Autorização GitHub
              </button>
              <button
                v-if="githubPaas?.connected && !accountUser.github_linked"
                type="button"
                @click="handleLinkGithub(true)"
                class="px-3 py-1.5 rounded bg-dock-success/20 border border-dock-success/40 text-dock-success font-medium cursor-pointer"
              >
                Vincular @{{ githubPaas.username }} já ativo
              </button>
            </div>

            <div
              v-if="ghDeviceFlow"
              class="p-3 rounded-lg bg-dock-surface border-2 border-dock-accent space-y-2"
            >
              <div class="text-[11px] text-dock-text">
                Copie o código abaixo e cole em <code>github.com/login/device</code>:
              </div>
              <div class="text-xl font-mono font-bold tracking-widest text-dock-accent text-center py-1.5 bg-dock-bg rounded border border-dock-border select-all">
                {{ ghDeviceFlow.user_code }}
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  @click="copyAndOpenGithubDevice"
                  class="px-3 py-1.5 rounded bg-dock-accent text-white font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  <Copy class="w-3.5 h-3.5" />
                  2. Copiar {{ ghDeviceFlow.user_code }} e Abrir GitHub
                  <ExternalLink class="w-3 h-3" />
                </button>
                <button
                  type="button"
                  @click="handleManualConfirmGithubDevice"
                  class="px-3 py-1.5 rounded bg-dock-success text-white font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 class="w-3.5 h-3.5" />
                  3. Já Autorizei — Confirmar Acesso
                </button>
              </div>
              <div class="text-[11px] text-dock-text-dim flex items-center gap-1.5">
                <RefreshCw class="w-3 h-3 animate-spin text-dock-accent" />
                <span>{{ ghDeviceStatusMsg || 'Aguardando confirmação no GitHub...' }}</span>
              </div>
            </div>
          </div>

          <!-- Opção 2: Vínculo/Login Direto com Usuário + Token GitHub -->
          <div class="p-3 rounded-lg bg-dock-bg border border-dock-border space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="font-medium text-dock-text">Opção 2 — Vincular / Logar via Token ou Usuário Git</span>
              <a
                href="https://github.com/settings/tokens/new?description=DeployDock-Account&scopes=repo,read:user,admin:repo_hook,read:packages"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11px] text-dock-accent hover:underline flex items-center gap-1"
              >
                Gerar Token no GitHub <ExternalLink class="w-3 h-3" />
              </a>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <input
                v-model="ghForm.username"
                type="text"
                placeholder="Usuário GitHub (ex: JeanMago)"
                class="bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
              <input
                v-model="ghForm.token"
                type="password"
                placeholder="Token ghp_xxxx (opcional)"
                class="bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none"
              />
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                @click="handleLinkGithub(false)"
                class="px-3 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium cursor-pointer"
              >
                Salvar Vínculo GitHub
              </button>
              <button
                type="button"
                @click="handleSwitchLoginGithub"
                class="px-3 py-1.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text font-medium flex items-center gap-1.5 cursor-pointer"
              >
                <LogIn class="w-3.5 h-3.5 text-dock-accent" />
                Autenticar Sessão com GitHub
              </button>
              <button
                v-if="accountUser.github_linked"
                type="button"
                @click="handleUnlinkGithub"
                class="px-2.5 py-1.5 rounded bg-dock-error/15 border border-dock-error/30 text-dock-error cursor-pointer ml-auto"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        <!-- Card B: Conta Google -->
        <div class="glass-panel p-5 space-y-4 border border-dock-border">
          <div class="flex items-center justify-between border-b border-dock-border pb-3">
            <div class="flex items-center gap-2.5">
              <div class="p-2 rounded-lg bg-dock-bg border border-dock-border text-dock-success">
                <Mail class="w-4 h-4" />
              </div>
              <div>
                <h3 class="font-semibold text-sm text-dock-text">Conta Google (SSO & Gmail)</h3>
                <p class="text-[11px] text-dock-text-dim">
                  Login rápido com Google e recebimento de alertas no Gmail/Workspace
                </p>
              </div>
            </div>
            <span
              class="px-2.5 py-1 rounded font-mono text-[10px] border"
              :class="
                accountUser.google_linked
                  ? 'bg-dock-success/15 text-dock-success border-dock-success/30'
                  : 'bg-dock-bg text-dock-text-dim border-dock-border'
              "
            >
              {{ accountUser.google_linked ? `Conectado (${accountUser.google_email})` : 'Não Vinculado' }}
            </span>
          </div>

          <!-- Opção 1: OAuth Device Flow Oficial do Google (google.com/device) -->
          <div class="p-3 rounded-lg bg-dock-bg border border-dock-border space-y-2.5">
            <div class="font-medium text-dock-text">
              Opção 1 — Autorização OAuth no Navegador (Código de Dispositivo Google)
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                @click="handleStartGoogleDevice"
                class="px-3 py-1.5 rounded bg-dock-success text-white font-medium flex items-center gap-1.5 cursor-pointer hover:opacity-90"
              >
                <Mail class="w-3.5 h-3.5" />
                1. Conectar pelo Navegador (OAuth Automático)
              </button>
            </div>

            <div
              v-if="googleDeviceFlow"
              class="p-3 rounded-lg bg-dock-surface border-2 border-dock-success space-y-2"
            >
              <div class="text-[11px] text-dock-text">
                Copie o código abaixo, clique em <strong>Abrir Google</strong> (<code>google.com/device</code>) e escolha sua conta Google:
              </div>
              <div class="text-xl font-mono font-bold tracking-widest text-dock-success text-center py-1 bg-dock-bg rounded border border-dock-border select-all">
                {{ googleDeviceFlow.user_code }}
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <button
                  type="button"
                  @click="copyAndOpenGoogleDevice"
                  class="py-2 px-3 rounded bg-dock-success text-white font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Copy class="w-3.5 h-3.5" />
                  2. Copiar Código e Abrir Google
                  <ExternalLink class="w-3 h-3" />
                </button>
                <button
                  type="button"
                  @click="handleManualPollGoogleDevice"
                  class="py-2 px-3 rounded bg-dock-accent text-white font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 class="w-3.5 h-3.5" />
                  3. Já Autorizei no Google — Confirmar Agora
                </button>
              </div>
              <div class="text-[11px] text-dock-text-dim flex items-center gap-1.5">
                <RefreshCw class="w-3 h-3 animate-spin text-dock-success" />
                <span>{{ googleDeviceStatusMsg || 'Aguardando confirmação em google.com/device...' }}</span>
              </div>
            </div>
          </div>

          <!-- Opção 2: Vínculo Direto Gmail + Senha de App Google (Ativa Envio Real de E-mails) -->
          <div class="p-3 rounded-lg bg-dock-bg border border-dock-border space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="font-medium text-dock-text">
                Opção 2 — E-mail Google + Senha de App (Ativa Envio Real no Gmail)
              </span>
              <a
                href="https://myaccount.google.com/apppasswords"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11px] text-dock-success hover:underline flex items-center gap-1"
              >
                Gerar Senha de App Google <ExternalLink class="w-3 h-3" />
              </a>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div>
                <label class="block text-dock-text-muted mb-1">E-mail da Conta Google *</label>
                <input
                  v-model="googleForm.email"
                  type="email"
                  placeholder="seuemail@gmail.com"
                  class="w-full bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
                />
              </div>
              <div>
                <label class="block text-dock-text-muted mb-1">Nome na Conta Google</label>
                <input
                  v-model="googleForm.name"
                  type="text"
                  placeholder="Seu Nome"
                  class="w-full bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 text-dock-text outline-none"
                />
              </div>
            </div>

            <div>
              <label class="block text-dock-text-muted mb-1">
                Senha de App do Google (16 letras — opcional, autentica no Gmail e ativa envio real de alertas por e-mail)
              </label>
              <input
                v-model="googleForm.app_password"
                type="password"
                placeholder="xxxx xxxx xxxx xxxx (gerada em myaccount.google.com/apppasswords)"
                class="w-full bg-dock-surface border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text outline-none focus:border-dock-success"
              />
            </div>

            <div class="flex flex-wrap items-center gap-2 pt-1">
              <button
                type="button"
                @click="handleLinkGoogle"
                class="px-3.5 py-1.5 rounded bg-dock-success text-white font-medium cursor-pointer hover:opacity-90"
              >
                Vincular Conta Google
              </button>
              <button
                type="button"
                @click="handleSwitchLoginGoogle"
                class="px-3 py-1.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text font-medium flex items-center gap-1.5 cursor-pointer"
              >
                <LogIn class="w-3.5 h-3.5 text-dock-success" />
                Autenticar Sessão com Google
              </button>
              <button
                v-if="accountUser.google_linked"
                type="button"
                @click="handleUnlinkGoogle"
                class="px-2.5 py-1.5 rounded bg-dock-error/15 border border-dock-error/30 text-dock-error cursor-pointer ml-auto"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. Perfil & Preferências de Notificações por E-mail -->
      <div class="glass-panel p-5 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-dock-border pb-3">
          <div>
            <h3 class="font-semibold text-sm text-dock-text flex items-center gap-2">
              <Bell class="w-4 h-4 text-dock-accent" />
              Perfil & Notificações por E-mail da Minha Conta
            </h3>
            <p class="text-[11px] text-dock-text-dim mt-0.5">
              Defina como deseja receber mensagens e alertas de Deploy, Rollback e Segurança no seu e-mail.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              @click="handleTestEmailAlert"
              :disabled="testingEmail"
              class="px-3 py-1.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text font-medium flex items-center gap-1.5 cursor-pointer"
            >
              <Send class="w-3.5 h-3.5 text-dock-accent" />
              {{ testingEmail ? 'Enviando...' : 'Testar E-mail na Minha Conta' }}
            </button>
            <button
              type="button"
              @click="handleSaveProfile"
              :disabled="savingProfile"
              class="px-3.5 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium cursor-pointer"
            >
              {{ savingProfile ? 'Salvando...' : 'Salvar Perfil & E-mail' }}
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label class="block text-dock-text-muted mb-1">Nome Completo / Exibição</label>
            <input
              v-model="profileForm.full_name"
              type="text"
              class="w-full bg-dock-bg border border-dock-border rounded px-3 py-1.5 text-dock-text outline-none focus:border-dock-accent"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">E-mail Principal para Alertas</label>
            <input
              v-model="profileForm.email"
              type="email"
              class="w-full bg-dock-bg border border-dock-border rounded px-3 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
            />
          </div>
          <div>
            <label class="block text-dock-text-muted mb-1">URL do Avatar (Opcional)</label>
            <input
              v-model="profileForm.avatar_url"
              type="text"
              placeholder="https://avatars.githubusercontent.com/..."
              class="w-full bg-dock-bg border border-dock-border rounded px-3 py-1.5 font-mono text-dock-text outline-none focus:border-dock-accent"
            />
          </div>
        </div>

        <div class="p-3 rounded bg-dock-bg border border-dock-border flex flex-wrap items-center gap-6">
          <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text">
            <input type="checkbox" v-model="profileForm.email_notifications" class="accent-dock-accent" />
            <span>Receber Notificações por E-mail nesta conta</span>
          </label>
          <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text">
            <input type="checkbox" v-model="profileForm.notify_deploy_email" class="accent-dock-accent" />
            <span>Avisar sobre Deploys & Rollbacks por E-mail</span>
          </label>
          <label class="inline-flex items-center gap-2 cursor-pointer text-dock-text">
            <input type="checkbox" v-model="profileForm.notify_security_email" class="accent-dock-accent" />
            <span>Avisar sobre Bloqueios WAF & Segurança por E-mail</span>
          </label>
        </div>
      </div>

      <!-- 4. Segurança: Senha Local, 2FA (TOTP) e Sessões Recentes -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div class="glass-panel p-5 space-y-4">
          <h3 class="font-semibold text-sm text-dock-text flex items-center gap-2 border-b border-dock-border pb-2.5">
            <KeyRound class="w-4 h-4 text-dock-accent" />
            Senha Local & Autenticação 2FA (TOTP)
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <input
              v-model="currentPass"
              type="password"
              placeholder="Senha atual"
              class="bg-dock-bg border border-dock-border rounded px-3 py-1.5 font-mono text-dock-text outline-none"
            />
            <input
              v-model="newPass"
              type="password"
              placeholder="Nova senha (mín. 6 caracteres)"
              class="bg-dock-bg border border-dock-border rounded px-3 py-1.5 font-mono text-dock-text outline-none"
            />
          </div>
          <button
            type="button"
            @click="handleChangePassword"
            :disabled="changingPass"
            class="px-3.5 py-1.5 rounded bg-dock-accent hover:bg-dock-accent-hover text-white font-medium cursor-pointer"
          >
            {{ changingPass ? 'Atualizando...' : 'Alterar Senha Local' }}
          </button>

          <div class="pt-3 border-t border-dock-border space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="font-medium text-dock-text flex items-center gap-1.5">
                <Shield class="w-3.5 h-3.5 text-dock-accent" />
                Autenticação em 2 Etapas (TOTP)
              </span>
              <span
                class="px-2 py-0.5 rounded font-mono text-[10px]"
                :class="
                  accountUser.totp_enabled
                    ? 'bg-dock-success/15 text-dock-success'
                    : 'bg-dock-bg text-dock-text-dim'
                "
              >
                {{ accountUser.totp_enabled ? 'ATIVO' : 'INATIVO' }}
              </span>
            </div>

            <div v-if="!accountUser.totp_enabled" class="space-y-2">
              <button
                v-if="!totpSetupData"
                type="button"
                @click="handleSetup2FA"
                class="px-3 py-1.5 rounded bg-dock-surface hover:bg-dock-panel border border-dock-border text-dock-text cursor-pointer"
              >
                Gerar Chave 2FA (Google Authenticator / Authy)
              </button>
              <div v-else class="p-2.5 rounded bg-dock-bg border border-dock-border space-y-2">
                <div class="font-mono text-[11px] text-dock-accent break-all">
                  Segredo Base32: {{ totpSetupData.secret }}
                </div>
                <div class="flex gap-2">
                  <input
                    v-model="totpOtpCode"
                    type="text"
                    maxlength="6"
                    placeholder="Código de 6 dígitos"
                    class="flex-1 bg-dock-surface border border-dock-border rounded px-2.5 py-1 font-mono text-dock-text"
                  />
                  <button
                    type="button"
                    @click="handleEnable2FA"
                    class="px-3 py-1 rounded bg-dock-success text-white font-medium cursor-pointer"
                  >
                    Ativar 2FA
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="flex gap-2">
              <input
                v-model="totpDisableCode"
                type="text"
                maxlength="6"
                placeholder="Código TOTP atual para desativar"
                class="flex-1 bg-dock-bg border border-dock-border rounded px-2.5 py-1.5 font-mono text-dock-text"
              />
              <button
                type="button"
                @click="handleDisable2FA"
                class="px-3 py-1.5 rounded bg-dock-error/15 border border-dock-error/30 text-dock-error cursor-pointer"
              >
                Desativar 2FA
              </button>
            </div>
          </div>
        </div>

        <!-- Histórico de Acessos da Minha Conta -->
        <div class="glass-panel p-5 space-y-3">
          <h3 class="font-semibold text-sm text-dock-text flex items-center gap-2 border-b border-dock-border pb-2.5">
            <Laptop class="w-4 h-4 text-dock-accent" />
            Meus Acessos & Sessões Recentes ({{ accountSessions.length }})
          </h3>
          <div v-if="accountSessions.length === 0" class="py-6 text-center text-dock-text-dim">
            Nenhuma sessão registrada ainda.
          </div>
          <div v-else class="max-h-56 overflow-y-auto space-y-2 pr-1">
            <div
              v-for="sess in accountSessions"
              :key="sess.session_id"
              class="p-2.5 rounded bg-dock-bg border border-dock-border flex items-center justify-between gap-2"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2 font-mono">
                  <span class="font-semibold text-dock-text uppercase">{{ sess.provider }}</span>
                  <span class="text-dock-text-dim">• IP {{ sess.ip }}</span>
                </div>
                <div class="text-[10px] text-dock-text-dim truncate mt-0.5">
                  {{ sess.logged_in_at }}
                </div>
              </div>
              <span
                class="px-2 py-0.5 rounded font-mono text-[10px] shrink-0"
                :class="
                  sess.active
                    ? 'bg-dock-success/15 text-dock-success'
                    : 'bg-dock-surface text-dock-text-dim'
                "
              >
                {{ sess.active ? 'Ativa' : 'Encerrada' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
